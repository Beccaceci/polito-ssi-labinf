#!/bin/bash

mkdir tree
cd tree

for DIR1 in a b c; do
   mkdir $DIR1
   for DIR2 in x y z; do
      mkdir $DIR1/$DIR2
      for FNAME in f1 f2 f3 f4 f5; do
         echo "Questo e' il file $FNAME in $DIR1/$DIR2." > $DIR1/$DIR2/$FNAME
      done
   done
done
