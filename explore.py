import h5py
import numpy as np
import pandas as pd

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


