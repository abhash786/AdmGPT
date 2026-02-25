import requests
import sys

BASE_URL = "http://127.0.0.1:8000"

def run_test():
    print("1. Testing Login...")
    user_name = "testuser"
    resp = requests.post(f"{BASE_URL}/login", json={"user_name": user_name})
    if resp.status_code != 200:
        print(f"Login failed: {resp.text}")
        sys.exit(1)
    
    token_data = resp.json()
    token = token_data["access_token"]
    print(f"   Login successful. Token received.")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n2. Testing Start Chat...")
    # Note: no body needed now, user inferred from token
    resp = requests.post(f"{BASE_URL}/chat/start", json={}, headers=headers)
    if resp.status_code != 200:
        print(f"Start chat failed: {resp.text}")
        sys.exit(1)
        
    start_data = resp.json()
    conv_id = start_data["conversation_id"]
    print(f"   Chat started. ID: {conv_id}")
    
    print("\n3. Testing Send Message (to generate title)...")
    message = "Tell me a very short joke about python."
    # We use stream=True but just read the content to ensure it processes
    resp = requests.post(
        f"{BASE_URL}/chat", 
        json={"conversation_id": conv_id, "message": message}, 
        headers=headers,
        stream=True
    )
    if resp.status_code != 200:
        print(f"Chat failed: {resp.text}")
        sys.exit(1)
    
    # Consume stream
    print("   Receiving response...", end="")
    for line in resp.iter_lines():
        pass
    print(" Done.")
    
    print("\n4. Testing List Conversations...")
    resp = requests.get(f"{BASE_URL}/conversations", headers=headers)
    if resp.status_code != 200:
        print(f"List conversations failed: {resp.text}")
        sys.exit(1)
        
    conversations = resp.json()
    print(f"   Found {len(conversations)} conversations.")
    
    # Check if our conversation is there and title is updated
    found = False
    for c in conversations:
        if c["id"] == conv_id:
            print(f"   Found current conversation. Title: '{c['title']}'")
            if c["title"] == "New Conversation":
                print("   WARNING: Title was not updated.")
            else:
                print("   SUCCESS: Title updated.")
            found = True
            break
            
    if not found:
        print("   ERROR: Current conversation not found in list.")
        sys.exit(1)

    print("\n5. Testing Get Conversation Detail...")
    resp = requests.get(f"{BASE_URL}/conversations/{conv_id}", headers=headers)
    if resp.status_code != 200:
        print(f"Get details failed: {resp.text}")
        sys.exit(1)
        
    detail = resp.json()
    msg_count = len(detail["messages"])
    print(f"   Retrieved details. Message count: {msg_count}")
    if msg_count >= 2: # User msg + Assistant msg (streamed)
        print("   SUCCESS: History retrieved.")
    else:
        print("   WARNING: History seems incomplete.")

if __name__ == "__main__":
    run_test()
