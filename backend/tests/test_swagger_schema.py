import requests
import sys

def test_swagger_security():
    url = "http://localhost:8000/openapi.json"
    try:
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Failed to fetch openapi.json: {response.status_code}")
            sys.exit(1)
        
        schema = response.json()
        
        # Check securitySchemes
        components = schema.get("components", {})
        security_schemes = components.get("securitySchemes", {})
        
        if not security_schemes:
            print("ERROR: No securitySchemes found in OpenAPI schema.")
            sys.exit(1)
            
        print("Security Schemes found:", security_schemes.keys())
        
        # Check HTTPBearer
        has_bearer = False
        for name, scheme in security_schemes.items():
            if scheme.get("type") == "http" and scheme.get("scheme") == "bearer":
                has_bearer = True
                print(f"SUCCESS: Found HTTPBearer scheme '{name}'")
                break
        
        if not has_bearer:
            print("ERROR: HTTPBearer scheme not found.")
            sys.exit(1)

        # Check if endpoints are secured
        paths = schema.get("paths", {})
        chat_path = paths.get("/chat", {})
        post_op = chat_path.get("post", {})
        security = post_op.get("security", [])
        
        if not security:
            print("WARNING: /chat endpoint does not seem to have security requirements.")
        else:
            print(f"SUCCESS: /chat endpoint has security: {security}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_swagger_security()
