from ldap3 import Connection, Server, ALL
def validate_user_mail(mailId):
    try:
        conn = Connection(Server(host="ldaps://corpadssl.intel.com", port=3269,get_info=ALL),user="GAR\sys_toolscps", password="intel@123456789012345", raise_exceptions=True, auto_bind=True)
        if conn.search(search_base='DC=corp,DC=intel,DC=com', search_filter=f"(&(mail={mailId}))", attributes=['displayName','name','mail']):
            return conn.entries[0]['mail']
        else:
            return "Not Found"
    except Exception as e:
        return e