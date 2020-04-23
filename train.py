from tensorflow import keras
import numpy as np
import tensorflow as tf
import pickle

# filename = "dataset-no-flip"
filename = "dataset"
with open("models/" + filename + ".pickle", "rb") as f:
    dataset = list(pickle.load(f))

size = 100

def input_dataset():
    for each_game in list(dataset):
        for each_move in each_game:
            # print(each_move)
            data = ([each_move[1][2]/3500]) # roughly normalized avg rating
            move_evals = each_move[1][0]

            data.extend(move_evals)

            data.extend([0]*(size-len(data)))
            # print(len(move_evals))
            assert len(data) == size
            yield data

def gen_label():
    for each_game in list(dataset):
        for each_move in each_game:
            yield (each_move[0])

# print(list(input_dataset()))
model = keras.Sequential([
    # keras.layers.Dense(128, activation='relu'),
    keras.layers.Dense(size, activation='tanh'),
    keras.layers.Dropout(0.4),
    keras.layers.Dense(32),
    keras.layers.Dense(size)
    # keras.layers.Dense(128)

    # keras.layers.Dense(128, activation='sigmoid')
])

# model.compile(optimizer='adam',
# keras.optimizers.Adam(learning_rate=0.001, beta_1=0.9, beta_2=0.99, amsgrad=False),
model.compile(optimizer='adam',
              loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
              metrics=['accuracy'])

input_data = np.array(list(input_dataset()))
labels = np.array(list(gen_label()))
model.fit(input_data, 
          labels, 
          epochs=50, 
          validation_split=0.2,
          batch_size=64)

model.summary()
model.save("models/" + filename + ".h5")
