import sqlite3 as sq

async def db_start():
    global db, cur

    db = sq.connect('new.db')
    cur = db.cursor()

    cur.execute('''CREATE TABLE IF NOT EXISTS users(
                    user_id TEXT PRIMARY KEY)''')
    db.commit()

    cur.execute('''CREATE TABLE IF NOT EXISTS tags(
                tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
                tag_number INTEGER, 
                tag_name TEXT, 
                user_id TEXT)''')
    db.commit()

    cur.execute('''CREATE TABLE IF NOT EXISTS notes(
                    note_id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    tag_id TEXT,
                    tag_number TEXT,
                    user_id TEXT, 
                    content TEXT)''')
    db.commit()


async def create_user(user_id, chat_id):
    user = cur.execute('SELECT 1 FROM users WHERE user_id == "{key}"'.format(key=user_id)).fetchone()
    if not user:
        cur.execute('INSERT INTO users VALUES(?)', (user_id,))
        db.commit()

async def create_tag(tag_name, user_id):
    db.commit()
    tag_number = 0
    max_id = cur.execute('SELECT MAX(tag_id) FROM tags').fetchone()[0]
    new_tag_id = 1 if max_id is None else max_id + 1

    cur.execute('INSERT INTO tags (tag_id, tag_number, tag_name, user_id) VALUES (?, ?, ?, ?)',
                (new_tag_id, await second_user_tag(user_id=user_id), tag_name, user_id))
    db.commit()

async def second_user_tag(user_id):
    tag_number = 0
    max_tag_number = cur.execute(f'SELECT MAX(tag_number) FROM tags WHERE user_id = {user_id}').fetchone()[0]
    new_max_tag_number = 1 if max_tag_number is None else max_tag_number + 1
    db.commit()
    return new_max_tag_number

async def count_tag(user_id):
    num = cur.execute(f'SELECT COUNT(*) FROM tags WHERE user_id = "{user_id}"').fetchone()[0]
    db.commit()
    if num:
        return num
    return None

async def show_tags(user_id):
    tags_list = []
    tags = cur.execute(f'SELECT * FROM tags WHERE user_id = "{user_id}"').fetchall()
    db.commit()
    for i in tags:
        tags_list.append(i[2])
    return tags_list

async def find_tag_id(tag_name):
    tags_list = cur.execute(f'SELECT tag_id FROM tags WHERE tag_name = "{tag_name}"').fetchone()
    db.commit()
    if tags_list is not None:
        return tags_list
    else:
        raise TypeError(f'Тэг с именем "{tag_name}" не найден.')

async def check_tag(tag_number, user_id):
    tags = cur.execute(f'SELECT * FROM tags WHERE (tag_number == {tag_number} AND user_id = {user_id})').fetchone()
    db.commit()
    if tags:
        return tags
    return []

async def show_notes(tag_id):
    notes = cur.execute(f'SELECT * FROM notes WHERE tag_id == {int(tag_id)}').fetchall()
    db.commit()
    if notes:
        return notes
    else:
        return None

async def add_content(tag_number, user_id, content):
    result = await find_tag_by_number(user_id, tag_number)
    cur.execute(f'INSERT INTO notes (tag_id, tag_number, user_id, content) VALUES (?, ?, ?, ?)', (result, tag_number, user_id, content))
    db.commit()

async def find_tag_by_number(user_id, tag_number):
    result = cur.execute(f'SELECT * FROM tags WHERE user_id = {user_id} AND tag_number = {tag_number}').fetchone()[0]
    db.commit()
    if result:
        return result
    return None

async def delete_tag(user_id, tag_number):
    result = await find_tag_by_number(user_id, tag_number)
    cur.execute(f'DELETE FROM notes WHERE tag_id = ? AND user_id = ?', (int(result), user_id))
    db.commit()
    cur.execute(f'DELETE FROM tags WHERE tag_id = ?', (int(result),))
    db.commit()