import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials in .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
logger = logging.getLogger(__name__)

def load_to_db(phone: str, scam_type: str, description: str):
    """
    ETL Load: Отправляет номер в БД.
    Делает Select -> Insert или Update (т.к. supabase-py иногда криво делает чистый upsert без Primary Key)
    """
    try:

        response = supabase.table("phone_numbers").select("id, report_count").eq("phone", phone).execute()
        
        if response.data:
            existing = response.data[0]
            new_count = existing.get("report_count", 0) + 1
            supabase.table("phone_numbers").update({
                "report_count": new_count,
                "last_updated": datetime.utcnow().isoformat()
            }).eq("phone", phone).execute()
            logger.info(f"🔄 Updated: {phone} (Count: {new_count})")
        else:
            supabase.table("phone_numbers").insert({
                "phone": phone,
                "scam_type": scam_type,
                "risk_level": "dangerous",
                "risk_score": 90,
                "report_count": 1,
                "description": description[:250], 
                "last_updated": datetime.utcnow().isoformat()
            }).execute()
            logger.info(f"✅ Inserted: {phone} ({scam_type})")
            
    except Exception as e:
        logger.error(f"❌ DB Error for {phone}: {str(e)}")