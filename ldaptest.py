from ldap3 import Connection, Server, ALL

c = Connection(Server(host="ldaps://corpadssl.intel.com", port=3269,get_info=ALL),user="GAR\mgovin1x", password="gensim@987", raise_exceptions=True, auto_bind=True)
c.search(search_base='DC=corp,DC=intel,DC=com',search_filter="(&(objectcategory=person)(objectclass=user)(intelflags=1)(sAMAccountName=mgovin1x))")
c.entries
c.search(search_base='DC=corp,DC=intel,DC=com', search_filter="(&(objectcategory=person)(objectclass=user)(intelflags=1)(sAMAccountName=ssembulx))", attributes='memberOf')
c.entries
c.search(search_base='OU=Workers,DC=gar,DC=corp,DC=intel,DC=com', search_filter="(memberOf=CN=UST_DEV_SIV)", attributes=['mail','name'])
c.entries