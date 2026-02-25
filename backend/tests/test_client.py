import requests
import json
import sys

def test_chat():
    base_url = "http://localhost:8000"
    
    print("MCP Client Started. Type 'exit' or 'quit' to stop.")
    print("-" * 50)
    
    # 1. Start Chat Session (with Login)
    user_name = input("Enter your name: ").strip() or "User"
    try:
        # Login first to get token
        login_resp = requests.post(f"{base_url}/login", json={"user_name": user_name})
        login_resp.raise_for_status()
        token_data = login_resp.json()
        token = token_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("Login successful.")

        start_resp = requests.post(f"{base_url}/chat/start", json={}, headers=headers)
        start_resp.raise_for_status()
        start_data = start_resp.json()
        conversation_id = start_data["conversation_id"]
        print(f"\nAI: {start_data['message']}")
    except Exception as e:
        print(f"Error starting chat: {e}")
        return

    print(f"Session Started (ID: {conversation_id})")
    print("-" * 50)
    
    url = f"{base_url}/chat"
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            if user_input.lower() in ["exit", "quit"]:
                print("Exiting...")
                break
            
            if not user_input:
                continue

            data = {"message": user_input, "conversation_id": conversation_id}
            
            print("AI: ", end="", flush=True)
            
            with requests.post(url, json=data, headers=headers, stream=True) as response:
                if response.status_code != 200:
                    print(f"\nError: {response.status_code}")
                    print(response.text)
                    continue

                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode('utf-8')
                        if decoded_line.startswith("data: "):
                            data_str = decoded_line[6:]
                            if "[DONE]" in data_str:
                                break
                            try:
                                event = json.loads(data_str)
                                if event["type"] == "token":
                                    sys.stdout.write(event["content"])
                                    sys.stdout.flush()
                                elif event["type"] == "thought":
                                    sys.stdout.write("\n")
                                    print(f"[THOUGHT]: {event['content']}")
                                    sys.stdout.write("AI: ") # Re-prompt prefix for continuation
                                    sys.stdout.flush()
                                elif event["type"] == "question":
                                    sys.stdout.write("\n")
                                    print(f"[QUESTION]: {event['content']}")
                                    sys.stdout.write("AI: ") 
                                    sys.stdout.flush()
                            except json.JSONDecodeError:
                                pass
                print() # Newline at end of response

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\nError: {e}")

if __name__ == "__main__":
    test_chat()
