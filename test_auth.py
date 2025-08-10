#!/usr/bin/env python3

from config_loader import ConfigLoader
from services import AuthService

def test_auth():
    print("Testing authentication...")
    
    # Load config
    config = ConfigLoader().config
    print("Config loaded successfully")
    
    # Print users from config
    print("\nUsers in config:")
    for user in config["accounts"]["users"]:
        print(f"  User: {user['username']}, Password: {user['password']}")
    
    print("\nAdmins in config:")
    for admin in config["accounts"]["admins"]:
        print(f"  Admin: {admin['username']}, Password: {admin['password']}")
    
    # Create auth service
    auth = AuthService(config)
    print("\nAuthService created")
    
    # Test login with user1
    print("\nTesting user1 login...")
    result = auth.login("user1", "pass1", "user")
    print(f"Login result for user1: {result}")
    
    # Test login with admin
    print("\nTesting admin login...")
    result = auth.login("admin", "adminpass", "admin")
    print(f"Login result for admin: {result}")
    
    # Test wrong password
    print("\nTesting wrong password...")
    result = auth.login("user1", "wrongpass", "user")
    print(f"Login result with wrong password: {result}")

if __name__ == "__main__":
    test_auth()
