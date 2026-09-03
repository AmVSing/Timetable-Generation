"""data structures used in database searching"""

from typing import Optional

class Linked_list_node:
    """each node stores: secondary key (data), primary key (integer), and points to next node"""
    def __init__(self, data: str, primary_key: int, next_item: Optional["Linked_list_node"] = None) -> None:
        self.data = data # secondary key
        self.primary_key = primary_key # primary key related to the secondary key
        self.next_item = next_item # Pointer to next node in linked list

class Hash_table:
    """stores linked lists in buckets to be found"""
    def __init__(self, size: int) -> None:
        """Create a hash table of fixed size"""
        self.size = size # no. of buckets in hash table

        self.table = [None] * self.size # representation of table as 1d list, initialised to None
    
    def hash_function(self, data: str) -> int:
        # Using the djdb2 algorithm to hash a given key into a hash value, then storing in a bucket based on the remainder
        hash_value = 5381 # From my research, the number 5381 seems to result in the fewest collisions

        for char in data:
            # This carries out 5 binary left shifts then adds the hash value (equivalent to 33*hash_value), then adds the ascii for the character 
            hash_value = ((hash_value<<5) + hash_value) + ord(char) 
                
        bucket = hash_value % self.size # Place where the hash value will be stored
        return bucket

    def insert(self, primary_key: int, data: str) -> None:
        # insert (sk, pk) pair into hash table 
        index = self.hash_function(data) # Place where the data will be stored
        new_node = Linked_list_node(data, primary_key, self.table[index])
        self.table[index] = new_node # prepended



    def search(self, data: str) -> list[int] | None:
        # calculates hash, searches hash table, and returns list of pk results
        index = self.hash_function(data)
        current_node = self.table[index]
        primary_keys = [] 

        # if a linked list is already stored at the location, traverse through until the correct node is found, then return corresponding primary key
        while current_node != None:
            if current_node.data == data:
                primary_keys.append(current_node.primary_key)
            current_node = current_node.next_item # go to next node in linked list

        print(f"DEBUG: Hash Table Search for '{data}': {primary_keys}")
        return primary_keys # If there is a None type at the search location, return None
