import os
import errno
from os.path import isfile
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from pymongo import UpdateOne, ReplaceOne

import logging.handlers
from datetime import datetime
from distutils.util import strtobool
import pprint
import json

pp = pprint.PrettyPrinter(indent=4)

class Database:
  def __init__(self, arguments, config ):
    self.arguments = arguments
    self.config = config
    logging.basicConfig(
      format="[%s] " % (os.path.basename(__file__))  + '%(asctime)s %(levelname)-8s %(message)s',
      level=logging.INFO,
      datefmt='%Y-%m-%d %H:%M:%S')
    self.log = logging.getLogger(__name__)
    if self.arguments.debug:
      self.log.setLevel(logging.DEBUG)
  # def

  def conn_mongodb(self):
    authSource = 'admin'
    serverSelectionTimeoutMS = 10
    connectTimeoutMS = 20000 
    isSSL = False
    try:
      isSSL = bool(strtobool( self.config['MONGO_SSL'] ) )
      ssl_ca_certs = self.config['MONGO_SSL_CA_CERTS']
      if not os.path.isfile(ssl_ca_certs):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), ssl_ca_certs)
      ssl_certfile = self.config['MONGO_SSL_CERTFILE']
      if not os.path.isfile(ssl_certfile):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), ssl_certfile)
      ssl_keyfile = self.config['MONGO_SSL_KEYFILE']
      if not os.path.isfile(ssl_keyfile):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), ssl_keyfile)
      ssl_pem_passphrase = self.config['MONGO_SSL_PEM_PASSPHRASE']
    except KeyError as error:
      self.log.error("Env variable not found: " + str(error))
      isSSL = False
    except FileNotFoundError as error:
      self.log.error("File found: " + str(error))
      isSSL = False
    # try

    isAuth = True
    try:
      isAuth = bool(strtobool( self.config['MONGO_AUTH'] ) )
      username = self.config['MONGO_USERNAME']
      password = self.config['MONGO_PASSWORD']
    except KeyError as error:
      self.log.error("Env variable not found: " + str(error))
      isAuth = False
    # try

    host = None
    try:
      host = self.config['MONGO_HOST']
    except KeyError as error:
      self.log.error("Env variable not found: " + str(error))
      raise error

    self.client = None
    mode = 0
    if( isAuth ):
      mode += 10
    if( isSSL ):
      mode += 1

    if( mode == 0 ):
      self.log.info('Unsecure no auth connection to Database [%s]' % (host) )
      self.client = MongoClient( host, 
        serverSelectionTimeoutMS = serverSelectionTimeoutMS, 
        connectTimeoutMS = connectTimeoutMS )
    elif( mode == 1 ):
      self.log.info('SSL no auth connection to Database [%s]' % (host) )
      self.client = MongoClient( host, 
        ssl_ca_certs = ssl_ca_certs, 
        ssl_certfile = ssl_certfile, 
        ssl_keyfile = ssl_keyfile,
        ssl_pem_passphrase = ssl_pem_passphrase,
        ssl = isSSL,
        serverSelectionTimeoutMS = serverSelectionTimeoutMS, 
        connectTimeoutMS = connectTimeoutMS )
    elif( mode == 10 ):
      self.log.info('Unsecure authenticated connection to Database [%s]' % (host) )
      self.client = MongoClient( host,
        username = username,
        password = password,
        authSource = authSource,
        ssl = isSSL,
        serverSelectionTimeoutMS = serverSelectionTimeoutMS, 
        connectTimeoutMS = connectTimeoutMS )
    elif( mode == 11 ):
      self.log.info('SSL authenticated connection to Database [%s]' % (host) )
      self.client = MongoClient( host,
        username = username,
        password = password,
        ssl_ca_certs = ssl_ca_certs,
        ssl_certfile = ssl_certfile,
        ssl_keyfile = ssl_keyfile,
        ssl_pem_passphrase = ssl_pem_passphrase,
        authSource = authSource,
        ssl = isSSL,
        serverSelectionTimeoutMS = serverSelectionTimeoutMS, 
        connectTimeoutMS = connectTimeoutMS )

    # Selfcheck
    try:
      self.client.admin.command('ismaster')
    except Exception as error:
      self.log.error("Failed to connect to the Database: " + str(error))
      raise error
    # try
    self.server_info = self.client.server_info()
    self.log.info("Database connection OK, Server verison: " + self.server_info['version'] )
  # def

  def bulkUpsert(self, data, db_id, col_id ):
    # https://stackoverflow.com/questions/5292370/fast-or-bulk-upsert-in-pymongo
    operations = [ ]
    for key, value in data.items():
      # operations.append( UpdateOne( {'primaryEmail': key }, { '$set': value },upsert=True ) )
      operations.append( ReplaceOne( {'primaryEmail': key }, value, upsert = True ) )
    # for

    self.log.debug(pp.pformat(operations))
    db = self.client[db_id]
    try:
      result = db[col_id].bulk_write(operations)
    except BulkWriteError as bwe:
      pp.pprint(bwe.details)
    else:
      # https://pymongo.readthedocs.io/en/stable/api/pymongo/results.html
      info = "matched=%d modified=%d inserted=%d upserted=%d" % (result.matched_count, result.modified_count, result.inserted_count, result.upserted_count)
      self.log.info("bulkUpsert "+info)
      self.log.debug(pp.pformat(result.bulk_api_result))
  # def
# class
