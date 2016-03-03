from __future__ import print_function

import glob
import os
import sys
import time

import numpy
import pylab
import theano
import theano.tensor as T
from theano.tensor.shared_randomstreams import RandomStreams

from midi.utils import midiread, midiwrite
from keras.layers.core import Dense, TimeDistributedDense, Activation
from keras.layers.recurrent import SimpleRNN, LSTM
from keras.layers.embeddings import Embedding
from keras.models import Sequential
from keras.optimizers import SGD, RMSprop
numpy.random.seed(2209)


def maxProbs(pb):
	maxP = pb[0]
	maxIndex=0
	for i in numpy.arange(len(pb)):
		if pb[i] >pb[maxIndex]:
			maxIndex=i
	return i
	
		
class rnnmlp ():
	def __init__(self, r=(21, 109), dt=0.3):	
		self.r=r
		self.dt=dt	
		self.rnnModel = Sequential()
	def SimpleRNNModel(self, nHidden=120, lr = 0.01):
		self.rnnModel.add(SimpleRNN( nHidden, input_shape =( None, maxFeatures), activation='sigmoid', return_sequences=True))
		self.rnnModel.add(TimeDistributedDense(maxFeatures))
		self.rnnModel.add(Activation('softmax'))
		rmsprop = RMSprop(lr=lr, rho=0.9, epsilon=1e-06)
		self.rnnModel.compile(loss='categorical_crossentropy', optimizer=rmsprop)
	
	def LSTMModel(self, nHidden=150, lr = 0.01):
#		print('nHidden: %i\tlr: %.3f' % ( nHidden, lr) )
		self.rnnModel.add(LSTM( nHidden, activation='sigmoid', input_shape =( None, maxFeatures), return_sequences=True))
		self.rnnModel.add(TimeDistributedDense(nHidden))
		self.rnnModel.add(Activation('relu'))
		self.rnnModel.add(TimeDistributedDense(maxFeatures))
		self.rnnModel.add(Activation('softmax'))
		rmsprop = RMSprop(lr=lr, rho=0.9, epsilon=1e-06)
		self.rnnModel.compile(loss='categorical_crossentropy', optimizer=rmsprop)
	
	def train(self, files, weightSaveFile, batchSize=1, numEpoch=200):
		print('load data ---------------')
		assert len(files) > 0, 'Training set is empty!'
		dataset = [midiread(f, self.r, self.dt).piano_roll.astype(theano.config.floatX) for f in files]
		
		file_test=os.path.join(os.path.split(os.path.dirname(__file__))[0],
				'data','Major','test','*.mid')
		testdataset = [midiread(f, self.r, self.dt).piano_roll.astype(theano.config.floatX) for f in glob.glob(file_test)]
		print('load done --------------')
		try:
			for epoch in range(numEpoch):
				t0 = time.time()
				numpy.random.shuffle(dataset)
				costs = []
				accuracys = []
				for s, sequence in enumerate(dataset):
					y = numpy.hstack((sequence,numpy.zeros((sequence.shape[0],1)) ))
					x = numpy.roll(y, 1, axis=0)
					x[0,:]=0
					x[0,maxFeatures-1]=1
					cost, accuracy= self.rnnModel.train_on_batch(numpy.array([x]), numpy.array([y]), accuracy=True)
					costs.append(cost)
					accuracys.append(accuracy)

				print('epoch: %i/%i\tcost: %.5f\taccu: %.5f\ttime: %.4f s' % (epoch+1, numEpoch, numpy.mean(costs), numpy.mean(accuracys),time.time()-t0))
				sys.stdout.flush()
				test_accu=self.evaluate(testdataset)
				print('test_accu: %.5f' % ( numpy.mean(test_accu)) )
			self.rnnModel.save_weights(weightSaveFile)
		except KeyboardInterrupt:
			print('interrupt by user !')
	def evaluate(self, testdataset):
		test_accuracy =[]
		for s, sequence in enumerate(testdataset):
			test_y = numpy.hstack((sequence,numpy.zeros((sequence.shape[0],1)) ))
			test_x = numpy.roll(test_y, 1, axis=0)
			test_x[0,:]=0
			test_x[0,maxFeatures-1]=1
			cost, accu = self.rnnModel.test_on_batch(numpy.array([test_x]),numpy.array([test_y]), accuracy=True)
			test_accuracy.append(accu)
		return test_accuracy


	def generate(self, filename, nSteps=80 ,show=False):
		init_sequence = numpy.zero((1, nSteps +1, maxFeatures))
		init_sequence[:, 0, maxFeatures-1] = 1
		for i in numpy.arange(nSteps):
			probs = self.rnnModel.predict_proba(init_sequence, batchSize=1)[:, i, :]
			for j in numpy.arrange(len(init_sequence)):
				init_sequence[j, i+1, maxProbs(probs[j,:])] = 1

		generate_sq = [sq[1:].nonzero()[1] for sq in init_sequence] 
		midiwrite(filename, generate_sq, self.r, self.dt)

	def loadModel(self, weightSaveFile):
		self.rnn_model.load_weights(weightSaveFile)

if __name__=='__main__':
#input: nHidden, lr, saveFile
	maxFeatures = 88 + 1
	model = rnnmlp();
	#model.SimpleRNNModel(nHidden=150, lr=0.01)	
	model.LSTMModel(nHidden=int(sys.argv[1]), lr=float(sys.argv[2]))	
	file_path=os.path.join(os.path.split(os.path.dirname(__file__))[0],
				'data','Major','train','*.mid')
	model.train(glob.glob(file_path),sys.argv[3],batchSize=1, numEpoch=120)
	
