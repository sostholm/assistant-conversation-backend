from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

# Connect to your MongoDB database
client = MongoClient('mongodb://192.168.0.218:27017/')
db = client['assistant_conversation']  # replace with your database name
conversation_collection = db['conversations']  # replace with your collection name

# A function that inserts a conversation into the database

def add_or_update_conversation(conversation_id, messages):
    conversation = {
        "conversation_id": conversation_id,
        "messages": messages
    }

    try:
        conversation_collection.update_one(
            {"conversation_id": conversation_id},  # condition
            {"$set": conversation},  # new data
            upsert=True  # if conversation_id does not exist, insert a new document
        )
    except DuplicateKeyError:
        print("Error occurred while updating the conversation.")
        return False
    return True