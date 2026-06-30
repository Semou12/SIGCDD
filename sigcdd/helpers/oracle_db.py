

import oracledb

class SOracleDB:
    def __init__(self, dbname, username, password,host="localhost", port=1521,sid=None):
        """Constructor Method"""
        # Set connection object to None (initial value)
        self.connection = None
        self.host = host
        self.dbname = dbname
        self.username = username
        self.password = password
        self.port = port
        self.sid=sid

    def connect(self):
        """Connects to the oracle server and returns the db connection object"""

        try:
            if self.sid:
                dsn= "{}:{}/{}".format(self.host,self.port,self.sid)
                self.connection = oracledb.connect(user=self.username, password=self.password, sid=self.sid,dsn=dsn)
                #self.connection = oracledb.connect(user="sigcdv4", password="sigcdv4", sid="tresor1",dsn="10.6.0.35:1556/tresor1")

            else:self.connection =oracledb.connect(user=self.username, password=self.password,host=self.host, port=self.port, service_name=self.dbname)


        except Exception as err:
            raise Exception(err)
        finally:
            print(f"Connected to {self.host} as {self.username}.")

    def disconnect(self):
        """Closes the db connection"""
        if self.connection:
            self.connection.close()
            #print(f"Disconnected from host {self.host}")


    def get_rows(self,sql):
        res=None
        with self.connection.cursor() as cursor:
            #print("Get all rows via an iterator")
            cursor.execute(sql)
            res = cursor.fetchall()
        return res
