import os
import requests
import base64
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Marketplace Insights API(실제 판매완료가)는 eBay가 승인한 파트너에게만 열어주는
# 제한 공개(Limited Release) API라서, 승인 전에는 이 scope로 토큰 발급 자체가
# 거부될 수 있다. 그래서 "insights 포함 scope"를 먼저 시도하고, 실패하면
# Browse API만 되는 기본 scope로 재시도한다(승인 전에도 기존 기능은 그대로 동작).
INSIGHTS_SCOPE = "https://api.ebay.com/oauth/api_scope https://api.ebay.com/oauth/api_scope/buy.marketplace.insights"
BASIC_SCOPE = "https://api.ebay.com/oauth/api_scope"


class EbayScraper:
    def __init__(self):
        self.client_id = os.getenv("EBAY_CLIENT_ID")
        self.client_secret = os.getenv("EBAY_CLIENT_SECRET")
        self.auth_token = self._get_access_token()

    def _request_token(self, scope):
        url = "https://api.ebay.com/identity/v1/oauth2/token"
        auth_str = f"{self.client_id}:{self.client_secret}"
        encoded_auth = base64.b64encode(auth_str.encode()).decode()

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {encoded_auth}"
        }
        data = {"grant_type": "client_credentials", "scope": scope}

        try:
            response = requests.post(url, headers=headers, data=data)
            body = response.json()
            token = body.get("access_token")
            if not token:
                print(f"ℹ️  [eBay 토큰 발급 실패 - scope='{scope}'] status={response.status_code} body={body}")
            return token
        except Exception as e:
            print(f"❌ [eBay 토큰 발급 예외 - scope='{scope}'] {e}")
            return None

    def _get_access_token(self):
        if not self.client_id or not self.client_secret:
            return None

        # 1) Marketplace Insights까지 포함한 scope 먼저 시도 (승인된 경우에만 성공)
        token = self._request_token(INSIGHTS_SCOPE)
        if token:
            return token

        # 2) 실패하면 기본 Browse scope로 재시도 (Marketplace Insights 승인 전에도
        #    현재 판매중인 매물 조회는 계속 되도록)
        print("ℹ️  Marketplace Insights scope로 토큰 발급 실패 → 기본 scope로 재시도합니다.")
        return self._request_token(BASIC_SCOPE)

    def fetch_completed_sales(self, query, limit: int = 5):
        """실제 판매완료(sold) 가격 이력을 조회한다 (Marketplace Insights API).

        eBay로부터 이 API 사용 승인을 받기 전까지는 403 등으로 실패하며,
        그 경우 빈 리스트를 반환한다(호출부에서 fetch_recent_sales로 대체 조회).
        """
        if not self.auth_token:
            self.auth_token = self._get_access_token()

        if not self.auth_token:
            return []

        url = "https://api.ebay.com/buy/marketplace_insights/v1_beta/item_sales/search"
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "X-EBAY-C-MARKETPLACE-ID": "EBAY_US"
        }
        params = {"q": query, "limit": limit}

        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code != 200:
                print(
                    f"ℹ️  [eBay 판매완료 조회 불가] status={response.status_code} "
                    f"body={response.text[:300]} "
                    "(Marketplace Insights API 접근 권한이 아직 없을 수 있습니다)"
                )
                return []

            data = response.json()
            items = data.get("itemSales", [])
            if not items:
                print(f"ℹ️  [eBay 판매완료 조회] '{query}' 에 대한 판매완료 이력 0건")

            results = []
            for item in items:
                sold_price = item.get("lastSoldPrice") or {}
                raw_date = item.get("lastSoldDate", "")

                results.append({
                    "title": item.get("title", "No Title"),
                    "price": sold_price.get("value", "0"),
                    "currency": sold_price.get("currency", "USD"),
                    "sold_date": raw_date[:10] if raw_date else "Recent",
                    "link": item.get("itemWebUrl", ""),
                    "status": "sold",
                })
            return results
        except Exception as e:
            print(f"❌ [eBay 판매완료 조회 예외] {e}")
            return []

    def fetch_recent_sales(self, query):
        """현재 판매중인(활성) 리스팅을 조회한다 (Browse API).

        ⚠️ 이름과 달리 '판매완료가'가 아니라 '현재 등록된 판매 호가'다.
        실제 판매완료가가 필요하면 fetch_completed_sales를 우선 사용하고,
        이 함수는 그게 안 될 때의 대체(fallback) 용도로 쓴다.
        """
        # 토큰이 없으면 빈 리스트를 반환하여 500 에러 방지
        if not self.auth_token:
            self.auth_token = self._get_access_token()

        if not self.auth_token:
            return []

        url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "X-EBAY-C-MARKETPLACE-ID": "EBAY_US"
        }
        params = {"q": query, "limit": 5, "sort": "newlyListed"}

        try:
            response = requests.get(url, headers=headers, params=params)
            # 응답이 정상이 아닐 경우 빈 리스트 반환 (원인 확인을 위해 콘솔에 출력)
            if response.status_code != 200:
                print(f"❌ [eBay 검색 실패] status={response.status_code} body={response.text[:500]}")
                return []

            data = response.json()
            items = data.get("itemSummaries", [])
            if not items:
                print(f"ℹ️  [eBay 검색] '{query}' 에 대한 결과 0건 (total={data.get('total', 0)})")
            results = []

            for item in items:
                raw_date = item.get("itemCreationDate", "")
                formatted_date = raw_date[:10] if raw_date else "Recent"

                results.append({
                    "title": item.get("title", "No Title"),
                    "price": item.get("price", {}).get("value", "0"),
                    "currency": item.get("price", {}).get("currency", "USD"),
                    "sold_date": formatted_date,
                    "link": item.get("itemWebUrl", ""),
                    "status": "active",
                })
            return results
        except Exception as e:
            print(f"Scraper Error: {e}")
            return []  # 에러 발생 시 빈 리스트 반환하여 500 에러 방지
