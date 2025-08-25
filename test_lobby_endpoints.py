#!/usr/bin/env python3
"""
Test script to demonstrate the new lobby information endpoints.
Run this from the backend directory: python test_lobby_endpoints.py
"""

import requests
import json

def test_lobby_endpoints():
    """Test the new lobby information endpoints."""
    
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Lobby Information Endpoints")
    print("=" * 50)
    
    # Test 1: Get all lobbies (should be empty initially)
    print("1. Getting all lobbies (initial state)...")
    try:
        response = requests.get(f"{base_url}/lobby/")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Total lobbies: {data['total_lobbies']}")
            print(f"   ✅ Lobbies: {len(data['lobbies'])}")
        else:
            print(f"   ❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Create a test lobby
    print("\n2. Creating a test lobby...")
    try:
        response = requests.post(f"{base_url}/lobby/create", params={
            "max_players": 4,
            "adventure_id": 1
        })
        if response.status_code == 200:
            lobby_data = response.json()
            lobby_id = lobby_data["lobby_id"]
            print(f"   ✅ Created lobby: {lobby_id}")
        else:
            print(f"   ❌ Failed to create lobby: {response.status_code} - {response.text}")
            return
    except Exception as e:
        print(f"   ❌ Error creating lobby: {e}")
        return
    
    # Test 3: Get specific lobby info
    print(f"\n3. Getting specific lobby info for {lobby_id}...")
    try:
        response = requests.get(f"{base_url}/lobby/{lobby_id}")
        if response.status_code == 200:
            data = response.json()
            lobby = data["lobby"]
            print(f"   ✅ Lobby ID: {lobby['id']}")
            print(f"   ✅ Adventure: {lobby['adventure_title']} (ID: {lobby['adventure_id']})")
            print(f"   ✅ Players: {lobby['current_players']}/{lobby['max_players']}")
            print(f"   ✅ Game Started: {lobby['game_started']}")
            print(f"   ✅ Can Join: {lobby['can_join']}")
        else:
            print(f"   ❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 4: Get all lobbies (should show our created lobby)
    print("\n4. Getting all lobbies (after creation)...")
    try:
        response = requests.get(f"{base_url}/lobby/")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Total lobbies: {data['total_lobbies']}")
            for lobby in data['lobbies']:
                print(f"   ✅ Lobby {lobby['id']}: {lobby['adventure_title']} ({lobby['current_players']}/{lobby['max_players']} players)")
        else:
            print(f"   ❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 5: Test with invalid lobby ID
    print("\n5. Testing invalid lobby ID...")
    try:
        response = requests.get(f"{base_url}/lobby/invalid_id")
        if response.status_code == 404:
            print(f"   ✅ Correctly returned 404 for invalid lobby ID")
        else:
            print(f"   ❌ Unexpected response: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n🎉 Lobby endpoints test completed!")
    print("\nAPI Endpoints Summary:")
    print("- GET /lobby/           - Get all lobbies")
    print("- GET /lobby/{id}       - Get specific lobby info")
    print("- POST /lobby/create    - Create new lobby")

if __name__ == "__main__":
    print("Make sure your FastAPI server is running on http://localhost:8000")
    print("You can start it with: uvicorn main:app --host 0.0.0.0 --port 8000 --reload")
    print()
    test_lobby_endpoints()
