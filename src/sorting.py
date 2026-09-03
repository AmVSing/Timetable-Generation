"""Sorting helpers used by the legacy genetic algorithm."""

def merge_sort(items, reverse = False):
    """Recursive merge with multiprocessing to speed up sorting
        Multiprocessing removed due to issues with importing files."""
    if isinstance(items, set):
        items = list(items) # sets are inherently unordered, so i'm converting the set to list
    if len(items) <=1: # base case
        return items
    mid = len(items)//2 # split list by middle
    left = items[:mid]
    right = items[mid:]
    # if multiprocessing.current_process().name == "MainProcess": # This prevents daemonic processes having child processes
    #     with multiprocessing.Pool(3) as pool:
    #         left, right = pool.map(merge_sort, [left, right])
    # else:
    #     left = merge_sort(left)
    #     right = merge_sort(right) 
    left = merge_sort(left) # recursively break down left sub-list
    right = merge_sort(right) # recursively break down right sub-list
    sorted_items = merge(left, right) # sort

    if not reverse:
        return sorted_items
    else:
        return sorted_items[::-1] # reverse if required

def merge(left, right):
    """Merge helper function to merge sub-lists into one list"""
    index1 = 0 # set index for left sublist
    index2 = 0 # "" for right sublust
    final_list = []

    list_is_2D = isinstance(left[0], list) and len(left[0]) > 1 # Checks if list is 2D: if first item in left list is itself a list of length >1
    while index1 < len(left) and index2 < len(right):
        if list_is_2D: # if 2D, then sort by second item in each list
            left_value = left[index1][1]
            right_value = right[index2][1]
        else: # otherwise, just sort by the item
            left_value = left[index1]
            right_value = right[index2]

        if left_value > right_value: # if left item greater
            final_list.append(right[index2]) # add the right value
            index2 += 1
        else: # else right value is greater or elements are equal
            final_list.append(left[index1])
            index1 +=1
    final_list.extend(left[index1:]) # add all items remaining in left list
    final_list.extend(right[index2:]) # add all items remaining in right list
    return final_list
