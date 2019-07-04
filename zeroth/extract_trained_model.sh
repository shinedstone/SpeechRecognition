path="."

mkdir ~/zeroth
mkdir ~/zeroth/conf
mkdir ~/zeroth/extractor

cp ${path}/exp/chain/tdnn1a_sp/final.mdl ~/zeroth/
cp ${path}/exp/chain/tree_a/graph_tgsmall/words.txt ~/zeroth/
cp ${path}/exp/chain/tree_a/graph_tgsmall/HCLG.fst ~/zeroth/
cp ${path}/exp/chain/tree_a/graph_tgsmall/phones.txt ~/zeroth/
cp ${path}/exp/chain/tree_a/graph_tgsmall/phones/word_boundary.int ~/zeroth/
cp ${path}/conf/mfcc_hires.conf ~/zeroth/conf/mfcc.conf
cp ${path}/exp/nnet3/ivectors_train_clean_sp_hires/conf/ivector_extractor.conf ~/zeroth/conf/
cp ${path}/exp/nnet3/ivectors_train_clean_sp_hires/conf/online_cmvn.conf ~/zeroth/conf/
cp ${path}/exp/nnet3/ivectors_train_clean_sp_hires/conf/splice.conf ~/zeroth/conf/
cp ${path}/exp/nnet3/extractor/final.mat ~/zeroth/extractor/
cp ${path}/exp/nnet3/extractor/global_cmvn.stats ~/zeroth/extractor/
cp ${path}/exp/nnet3/extractor/final.dubm ~/zeroth/extractor/
cp ${path}/exp/nnet3/extractor/final.ie ~/zeroth/extractor/
cp ${path}/data/lang_test_tgsmall/G.fst ~/zeroth/
cp ${path}/data/lang_test_fglarge/G.carpa ~/zeroth/
