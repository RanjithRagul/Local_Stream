from seedrcc import Seedr

# 1. Start the device authorization
# This gets the 'user_code' (to type in) and 'device_code' (for the script)
codes = Seedr.get_device_code()

print(f"1. Go to: {codes.verification_url}")
print(f"2. Enter this code: {codes.user_code}")
input("\n3. Press Enter HERE after you have authorized it on the website...")

# 4. Exchange the device_code for the client/token
# The 'with' statement ensures the connection is closed properly
with Seedr.from_device_code(codes.device_code) as client:
    # Access the actual string from the Token object
    permanent_token = client.token.access_token
    
    print(f"\n✅ SUCCESS!")
    print(f"Your Permanent Token is: {permanent_token}")
    print("\nCopy the line above and put it in your .env file as:")
    print(f"seedr_token={permanent_token}")