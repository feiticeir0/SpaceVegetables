import sqlite3
from sqlite3 import Error

# Create database connection
def create_connection (db_file):
    """ Create a connection to a database
        specified by db_file 
    :param db_file: A database file
    :return: connection object or None
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except Error as e:
        print (e)


    return conn


def create_table (conn, create_table_sql):
    """ create a table from the create_table_sql statment
    :param conn: Connection object
    :param create_table_sql: a CREATE TABLE statment
    :return:
    """
    try:
        c = conn.cursor()
        c.execute (create_table_sql)
    except Error as e:
        print (e)



def main():
    database = r"spaceVegetables.db"
    sql_create_vegetables_table = """ CREATE TABLE "Vegetables" (
                                      "idVegetables"  INTEGER,
                                      "PH"    REAL DEFAULT 0.0,
                                      "TDS"   REAL DEFAULT 0.0,
                                      "waterPumpActive"   NUMERIC DEFAULT 0,
                                      "lightsActive"  NUMERIC DEFAULT 0,
                                      "airPumpActive" NUMERIC DEFAULT 0,
                                      "temperature"   REAL DEFAULT 0.0,
                                      "humidity"  REAL DEFAULT 0.0,
                                      "pressure"  REAL DEFAULT 0.0,
                                      "lightSensor"   REAL DEFAULT 0.0,
                                      "temperatureInside" REAL DEFAULT 0.0,
                                      "humidityInside"    REAL DEFAULT 0.0,
                                      "dateTime"  TEXT DEFAULT '0000-00-00 00:00:00',
                                      PRIMARY KEY("idVegetables" AUTOINCREMENT)
                                 ); """

    conn = create_connection(database)

    if conn is not None:
        create_table (conn, sql_create_vegetables_table)
    else:
        print ("Error ! Cannot create the database connection.")


if __name__ == '__main__':
    main()
