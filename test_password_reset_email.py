"""
Test password reset email functionality
"""
import asyncio
import httpx
import time
import asyncpg

# API Configuration
API_BASE_URL = "http://localhost:8000/api/v1"

# Test user email (use existing user)
TEST_EMAIL = "bsakweson@bakalr.com"


async def test_password_reset():
    """Test password reset request and email sending"""
    print("=" * 60)
    print("🧪 Testing Password Reset Email Flow")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        # 1. Request password reset
        print(f"\n📧 Requesting password reset for: {TEST_EMAIL}")
        
        response = await client.post(
            f"{API_BASE_URL}/password-reset/request",
            json={"email": TEST_EMAIL},
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Password reset request accepted")
        else:
            print("❌ Password reset request failed")
            return
        
        # 2. Wait for email to be sent (background task)
        print("\n⏳ Waiting 3 seconds for email to be sent...")
        await asyncio.sleep(3)
        
        # 3. Check database for email log
        print("\n📊 Checking email_logs table...")
        try:
            conn = await asyncpg.connect(
                host="localhost",
                port=5432,
                user="bakalr",
                password="bakalr_password",
                database="bakalr_cms"
            )
            
            # Get latest email log
            result = await conn.fetch("""
                SELECT 
                    to_email,
                    subject,
                    template_name,
                    status,
                    error_message,
                    created_at
                FROM email_logs
                WHERE to_email = $1
                ORDER BY created_at DESC
                LIMIT 1
            """, TEST_EMAIL)
            
            if result:
                row = result[0]
                print(f"\n📬 Latest Email Log:")
                print(f"  To: {row['to_email']}")
                print(f"  Subject: {row['subject']}")
                print(f"  Template: {row['template_name']}")
                print(f"  Status: {row['status']}")
                print(f"  Error: {row['error_message'] or 'None'}")
                print(f"  Created: {row['created_at']}")
                
                if row['status'] == 'SENT':
                    print("\n✅ PASSWORD RESET EMAIL SENT SUCCESSFULLY!")
                else:
                    print(f"\n❌ Email status is {row['status']}, not SENT")
            else:
                print(f"\n❌ No email log found for {TEST_EMAIL}")
            
            await conn.close()
            
        except Exception as e:
            print(f"\n❌ Database check failed: {e}")


async def main():
    await test_password_reset()


if __name__ == "__main__":
    asyncio.run(main())
