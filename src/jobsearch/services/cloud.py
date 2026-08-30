import os
from supabase import create_client


def configurado():
    return bool(os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_PUBLISHABLE_KEY'))


def cliente(access_token=None):
    url = os.getenv('SUPABASE_URL', '').strip()
    key = os.getenv('SUPABASE_PUBLISHABLE_KEY', '').strip()
    if not url or not key:
        raise RuntimeError('Faltan SUPABASE_URL y SUPABASE_PUBLISHABLE_KEY.')
    client = create_client(url, key)
    if access_token:
        client.postgrest.auth(access_token)
    return client
