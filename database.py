# -*- coding: utf-8 -*-
import os
from supabase import create_client, Client
from typing import List, Dict, Optional

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class ForceSubDB:
    
    @staticmethod
    def add_force_sub(main_chat_id: int, main_chat_title: str, 
                      target_chat_id: int, target_chat_title: str,
                      target_link: str, added_by: int) -> bool:
        """Add a force subscribe channel"""
        try:
            data = {
                "main_chat_id": main_chat_id,
                "main_chat_title": main_chat_title,
                "target_chat_id": target_chat_id,
                "target_chat_title": target_chat_title,
                "target_link": target_link,
                "added_by": added_by
            }
            supabase.table("force_subscribe").upsert(data).execute()
            return True
        except Exception as e:
            print(f"Error adding force sub: {e}")
            return False
    
    @staticmethod
    def remove_force_sub(main_chat_id: int, target_chat_id: int) -> bool:
        """Remove a force subscribe channel"""
        try:
            supabase.table("force_subscribe").delete().match({
                "main_chat_id": main_chat_id,
                "target_chat_id": target_chat_id
            }).execute()
            return True
        except Exception as e:
            print(f"Error removing force sub: {e}")
            return False
    
    @staticmethod
    def get_force_subs(main_chat_id: int) -> List[Dict]:
        """Get all force subscribe channels for a group"""
        try:
            response = supabase.table("force_subscribe").select("*").eq(
                "main_chat_id", main_chat_id
            ).execute()
            return response.data
        except Exception as e:
            print(f"Error getting force subs: {e}")
            return []
    
    @staticmethod
    def remove_all_force_subs(main_chat_id: int) -> bool:
        """Remove all force subscribe channels for a group"""
        try:
            supabase.table("force_subscribe").delete().eq(
                "main_chat_id", main_chat_id
            ).execute()
            return True
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    @staticmethod
    def get_all_groups() -> List[Dict]:
        """Get all unique groups with force sub"""
        try:
            response = supabase.table("force_subscribe").select(
                "main_chat_id, main_chat_title"
            ).execute()
            # Remove duplicates
            seen = set()
            unique = []
            for item in response.data:
                if item['main_chat_id'] not in seen:
                    seen.add(item['main_chat_id'])
                    unique.append(item)
            return unique
        except Exception as e:
            print(f"Error: {e}")
            return []
