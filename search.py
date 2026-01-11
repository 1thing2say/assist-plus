import sqlite3

DB_NAME = "transfer_data.db"

def search_programs(user_major_query, source_college_id=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # SQL query with a LIKE clause for partial matching
    # e.g., '%Computer%' finds "Computer Science", "Computer Engineering"
    query = f"%{user_major_query}%"
    
    sql = '''
        SELECT receiving_name, major_name, agreement_key
        FROM agreements
        WHERE major_name LIKE ?
    '''
    params = [query]

    # If user selected a specific Community College, filter by it
    if source_college_id:
        sql += " AND sending_id = ?"
        params.append(source_college_id)
        
    cursor.execute(sql, params)
    results = cursor.fetchall()
    conn.close()
    
    return results

# --- TEST THE SEARCH ---
user_input = "Computer Science"
my_cc_id = 110 # De Anza College

matches = search_programs(user_input, my_cc_id)

print(f"Found {len(matches)} matches for '{user_input}':")
for uni, major, key in matches[:10]: # Print top 10
    print(f"- {uni}: {major}")