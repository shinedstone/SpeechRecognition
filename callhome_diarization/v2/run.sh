. ./cmd.sh
. ./path.sh
set -e
tmpdir=$(date +%Y-%m-%d_%H:%M:%S)_$$
mfccdir=${tmpdir}/mfcc
vaddir=${tmpdir}/vad
datadir=${tmpdir}/data
expdir=${tmpdir}/exp
nnet_dir=exp/xvector_nnet_1a
nj=1
threshold=$1
audiopath=$2

# Prepare features
if [ ! -d $datadir ]; then
  mkdir -p $datadir
fi
trap 'rm -rf $tmpdir' EXIT

if [ -d $audiopath ]; then
  for file in $audiopath/*.wav; do
    name=$(basename "$file" ".wav")
    dur=$(sox --info -D $file)
    echo "$name $name" >> ${datadir}/spk2utt
    echo "$name $name" >> ${datadir}/utt2spk
    echo "$name $file" >> ${datadir}/wav.scp
    echo "$name $dur" >> ${datadir}/utt2dur
  done
elif [ -f $audiopath ]; then
  name=$(basename "$audiopath" ".wav")
  dur=$(sox --info -D $audiopath)
  echo "$name $name" >> ${datadir}/spk2utt
  echo "$name $name" >> ${datadir}/utt2spk
  echo "$name $audiopath" >> ${datadir}/wav.scp
  echo "$name $dur" >> ${datadir}/utt2dur
else
  echo "$audiopath is not valid"
  exit 1
fi

steps/make_mfcc.sh --mfcc-config conf/mfcc.conf --nj $nj --cmd "$train_cmd" --write-utt2num-frames true $datadir ${mfccdir}/log $mfccdir
utils/fix_data_dir.sh $datadir

sid/compute_vad_decision.sh --nj $nj --cmd "$train_cmd" $datadir ${vaddir}/log $vaddir
utils/fix_data_dir.sh $datadir

local/nnet3/xvector/prepare_feats.sh --nj $nj --cmd "$train_cmd" $datadir ${datadir}_cmn ${expdir}/test_cmn
cp $datadir/vad.scp ${datadir}_cmn/
cp $datadir/utt2dur ${datadir}_cmn/
utils/fix_data_dir.sh ${datadir}_cmn

diarization/vad_to_segments.sh --nj $nj --cmd "$train_cmd" ${datadir}_cmn ${datadir}_cmn_segmented
utils/fix_data_dir.sh ${datadir}_cmn_segmented

# Extract x-vectors
diarization/nnet3/xvector/extract_xvectors.sh --cmd "$train_cmd --mem 5G" --nj $nj --window 1.5 --period 0.75 --apply-cmn false --min-segment 0.5 $nnet_dir ${datadir}_cmn_segmented $expdir/xvectors

# Perform PLDA scoring
diarization/nnet3/xvector/score_plda.sh --cmd "$train_cmd --mem 4G" --nj $nj $nnet_dir/xvectors_callhome2 $expdir/xvectors $expdir/xvectors/plda_scores

# Cluster the PLDA scores using a stopping threshold.
diarization/cluster.sh --cmd "$train_cmd --mem 4G" --nj $nj --threshold $threshold $expdir/xvectors/plda_scores $expdir/xvectors/plda_scores

cat $expdir/xvectors/plda_scores/rttm
