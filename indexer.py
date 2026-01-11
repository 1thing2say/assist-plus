import sqlite3
import json
import os
import glob

# Configuration
DATA_DIR = "assist_data"
DB_NAME = "transfer_data.db"

def init_db():
    """Create the database and table schema"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # We create a table to store every agreement found
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agreements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sending_id INTEGER,
            sending_name TEXT,
            receiving_id INTEGER,
            receiving_name TEXT,
            major_name TEXT,
            agreement_key TEXT,
            year INTEGER
        )
    ''')
    
    # Create an index on major_name for fast searching
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_major ON agreements(major_name)')
    conn.commit()
    return conn

def index_files():
    conn = init_db()
    cursor = conn.cursor()
    
    # Find all JSON files
    files = glob.glob(os.path.join(DATA_DIR, "*_master.json"))
    print(f"Found {len(files)} files to index.")

    count = 0
    
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = f.read()
                # Skip empty files
                if not data: continue
                
                json_data = json.loads(data)
                
                # Handle dict structure with 'result' key
                if isinstance(json_data, dict) and 'result' in json_data:
                    result = json_data['result']
                    
                    # Parse institutions from JSON strings
                    sending_inst_str = result.get('sendingInstitution', '{}')
                    receiving_inst_str = result.get('receivingInstitution', '{}')
                    
                    try:
                        sending_inst = json.loads(sending_inst_str) if isinstance(sending_inst_str, str) else sending_inst_str
                        receiving_inst = json.loads(receiving_inst_str) if isinstance(receiving_inst_str, str) else receiving_inst_str
                    except:
                        sending_inst = {}
                        receiving_inst = {}
                    
                    # Extract institution names (they're in a names array)
                    sending_name = 'Unknown CC'
                    if sending_inst.get('names') and len(sending_inst['names']) > 0:
                        sending_name = sending_inst['names'][0].get('name', 'Unknown CC')
                    
                    receiving_name = 'Unknown Uni'
                    if receiving_inst.get('names') and len(receiving_inst['names']) > 0:
                        receiving_name = receiving_inst['names'][0].get('name', 'Unknown Uni')
                    
                    sending_id = sending_inst.get('id')
                    receiving_id = receiving_inst.get('id')
                    
                    # Extract majors from templateAssets
                    template_assets_str = result.get('templateAssets', '[]')
                    try:
                        template_assets = json.loads(template_assets_str) if isinstance(template_assets_str, str) else template_assets_str
                    except:
                        template_assets = []
                    
                    if not isinstance(template_assets, list):
                        template_assets = []
                    
                    # Each template asset is a major
                    for major in template_assets:
                        major_name = major.get('name', 'Unknown Major')
                        if not major_name or major_name == 'Unknown Major':
                            continue
                        
                        # Create a unique agreement key from filename + major name
                        file_basename = os.path.basename(file_path)
                        agreement_key = f"{file_basename}_{major_name}"
                        
                        cursor.execute('''
                            INSERT INTO agreements 
                            (sending_id, sending_name, receiving_id, receiving_name, major_name, agreement_key)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (
                            sending_id, 
                            sending_name, 
                            receiving_id, 
                            receiving_name, 
                            major_name, 
                            agreement_key
                        ))
                        count += 1
                
                # Also handle list structure (for backwards compatibility)
                elif isinstance(json_data, list):
                    for item in json_data:
                        send_inst = item.get('sendingInstitution', {})
                        recv_inst = item.get('receivingInstitution', {})
                        
                        sending_name = send_inst.get('name', 'Unknown CC')
                        receiving_name = recv_inst.get('name', 'Unknown Uni')
                        
                        major_name = item.get('label') or item.get('major') or "Unknown Major"
                        agreement_key = item.get('key')
                        
                        cursor.execute('''
                            INSERT INTO agreements 
                            (sending_id, sending_name, receiving_id, receiving_name, major_name, agreement_key)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (
                            send_inst.get('id'), 
                            sending_name, 
                            recv_inst.get('id'), 
                            receiving_name, 
                            major_name, 
                            agreement_key
                        ))
                        count += 1
                        
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            import traceback
            traceback.print_exc()

    conn.commit()
    conn.close()
    print(f"Indexing complete! Indexed {count} agreements.")

if __name__ == "__main__":
    index_files()