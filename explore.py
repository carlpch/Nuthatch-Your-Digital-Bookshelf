import h5py
import numpy as np
import pandas as pd
import json, configparser
import psycopg2 as psycopg
import pandas as pd
import tensorflow as tf
import tensorflow_hub as hub

def load_embedding():
	book_export = h5py.File('data/export1.hdf5','r')
	book_embedding = np.array(book_export['book_embedding'])
	return book_embedding

def load_bookinfo():
    return pd.read_csv('data/book_matrix.csv')


def showneighbors(target_id, embeddings, bookinfo):
    similarity_vector = np.dot(
        embeddings[target_id], 
        embeddings.T)
    neighbor_df = pd.DataFrame(
    {'bookID': bookinfo.bookID,
     'bookName': bookinfo.bookName,
     'bookAuthor': bookinfo.Authors,
     'bookYear': bookinfo.PublishYear,
     'sim_score':similarity_vector
     }
    )
    neighbor_df = neighbor_df[neighbor_df.index != target_id]
    return neighbor_df.sort_values('sim_score', ascending=False).head(5)

def showneighbors2(target_id, embeddings, bookinfo):
    conn, cur = postgres_connect()
    cur.execute("SELECT top5 FROM book WHERE title={}")
    data = cur.fetchall()
    neighbor_df = pd.DataFrame(
    {'bookID': bookinfo.bookID,
     'bookName': bookinfo.bookName,
     'bookAuthor': bookinfo.Authors,
     'bookYear': bookinfo.PublishYear,
     'sim_score':similarity_vector
     }
    )
    neighbor_df = neighbor_df[neighbor_df.index != target_id]
    return neighbor_df.sort_values('sim_score', ascending=False).head(5)

# def load_bookinfo2():
#     conn, cur = postgres_connect()
#     cur.execute("SELECT nuthatch_id, title FROM book")
#     data = cur.fetchall()
#     data = [{'nuthatch_id':row[0],'title':row[1].strip()} for row in data]
#     data = pd.DataFrame(data)
#     data = data.reset_index(drop=True)
#     # return pd.read_csv('data/book_matrix.csv')
#     return data

def postgres_connect():
    config=configparser.ConfigParser()
    config.read('postgres/config.ini')

    connection = psycopg.connect(
        host = config['nuthatch']['host'],
        database = config['nuthatch']['database'],
        user = config['nuthatch']['user'],
        password = config['nuthatch']['password']
        )

    cursor = connection.cursor()
    # return connection, cursor
    return connection, cursor

def postgres_query():
    conn, cur = postgres_connect()
    cur.execute("SELECT nuthatch_id, title, summary, year FROM book WHERE summary IS NOT NULL ORDER BY nuthatch_id")
    data = cur.fetchall()
    data = [{'nuthatch_id':row[0],'title':row[1].strip(),'summary':str(row[2]).replace('\n',''), 'year':row[3]} for row in data]
    data = pd.DataFrame(data)
    data = data.reset_index(drop=True)
    cur.close()
    conn.close()
    return data

# def load_hub():
#     embed = hub.load("https://tfhub.dev/google/Wiki-words-500-with-normalization/2")
#     return embed

def load_embedding2():
    t = h5py.File('data/candidates_emb2.hdf5','r')
    candidates_emb = np.array(t['candidates_emb'])
    return candidates_emb

def find_close_books(nuthatch_id, candidates_emb, data,top=5):
    key_loc = data[data['nuthatch_id']==nuthatch_id].index
    key_emb = candidates_emb[key_loc]
    losses = tf.keras.losses.cosine_similarity(key_emb, candidates_emb)
    top_candidates = np.argsort(losses)[:top+1]
    title = [data.title[i] for i in top_candidates if data.nuthatch_id[i] != nuthatch_id][:top]
    year = [data.year[i] for i in top_candidates if data.nuthatch_id[i] != nuthatch_id][:top]
    return list(zip(title, year))




