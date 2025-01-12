import hashlib
import hmac
import urllib.parse


class vnpay_order:
    requestData = {}
    responseData = {}

    def get_payment_url(self, vnpay_payment_url, secret_key):
        # Sắp xếp các tham số theo key
        query_params = sorted(self.requestData.items())
        print("Before encoding:", query_params)

        # Tạo chuỗi query với việc encode đặc biệt
        query_parts = []
        for key, val in query_params:
            # Encode giá trị với quote_plus thay vì quote
            value = urllib.parse.quote_plus(str(val))
            query_parts.append(f"{key}={value}")

        # Tạo chuỗi query
        query_string = '&'.join(query_parts)
        print("Generated Query String:", query_string)

        # Tạo HMAC SHA512
        hash_value = self.__hmacsha512(secret_key, query_string)
        print("Generated Hash Value:", hash_value)

        # Tạo URL thanh toán cuối cùng
        final_url = f"{vnpay_payment_url}?{query_string}&vnp_SecureHash={hash_value}"
        print("Final URL:", final_url)

        return final_url

    def validate_response(self, secret_key):
        try:
            # Lấy và xóa chữ ký từ response
            vnp_SecureHash = self.responseData.get('vnp_SecureHash', '')
            self.responseData.pop('vnp_SecureHash', None)
            self.responseData.pop('vnp_SecureHashType', None)

            # Tạo chuỗi hash từ response
            queryParams = sorted(
                [(key, str(value)) for key, value in self.responseData.items() if key.startswith('vnp_')],
                key=lambda x: x[0]
            )

            queryString = []
            for key, val in queryParams:
                encoded_value = urllib.parse.quote(str(val).strip(), safe='')
                queryString.append(f"{key}={encoded_value}")

            queryString = '&'.join(queryString)
            print('Generated Query String:', queryString)

            # Tính toán và so sánh chữ ký
            hashValue = self.__hmacsha512(secret_key, queryString)
            print('Generated Hash:', hashValue)
            print('VNPay Hash:', vnp_SecureHash)

            if vnp_SecureHash != hashValue:
                raise ValueError("Invalid Checksum")

            print("Valid Signature!")
            return True

        except Exception as e:
            print(f"Validation Error: {str(e)}")
            return False

    @staticmethod
    def __hmacsha512(key, data):
        byteKey = key.encode('utf-8')
        byteData = data.encode('utf-8')
        print("HMAC Input:")
        print(f"Key: {key}")
        print(f"Data: {data}")
        hash_value = hmac.new(byteKey, byteData, hashlib.sha512).hexdigest()
        print(f"HMAC Output: {hash_value}")
        return hash_value
