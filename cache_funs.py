import json

def check_and_trim(list_):
    if len(list_)>100:
        list_.pop(0)
    return list_


def check_if_in_list(list_,sub_id):
    for element in list_:
        if element["sub_id"]==sub_id:
            return True
        
def check_where_in_list(list_,sub_id):
    for i,element in enumerate(list_):
        print(element)
        print(sub_id)
        if element["sub_id"]==sub_id:
            return i
    return -1



def read_write(file_dir,read=True,list_=None):
    if read==True:
        try:
            with open(file_dir, 'r') as file:
                try:
                    return json.load(file)
                except json.JSONDecodeError:
                    # If JSON content is not valid, return an empty list
                    return []
            
        except FileNotFoundError:
             with open(file_dir, 'w') as file:
                json.dump([], file)
                return []
    else:
        with open(file_dir, 'w') as file:
                json.dump(list_, file)


