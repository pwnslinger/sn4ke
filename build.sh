#!/bin/bash
git clone --recurse-submodules --depth 1 -b wip/random_mutation https://github.com/pwnslinger/sn4ke.git

sudo apt-get update
sudo apt-get install -y git build-essential python3 python-venv

# install cmake
version=3.12
build=1
mkdir ~/temp
cd ~/temp
wget https://cmake.org/files/v$version/cmake-$version.$build.tar.gz
tar -xzvf cmake-$version.$build.tar.gz
cd cmake-$version.$build/
./bootstrap
make -j$(nproc)
sudo make install

cd ~/sn4ke

rm -rf ./venv
python3 -m venv ./venv
chmod +x ./venv/bin/activate
. ./venv/bin/activate

# install gtirb, ddisasm
sudo add-apt-repository ppa:mhier/libboost-latest
echo "deb [trusted=yes] https://grammatech.github.io/gtirb/pkgs/bionic ./" | sudo tee -a /etc/apt/sources.list.d/gtirb.list
sudo apt-get update
sudo apt-get install libgtirb gtirb-pprinter ddisasm

# install keystone
cd keystone
mkdir build
cd build
../make-share.sh
sudo make install
sudo ldconfig
cd ../../

# install capstone
cd capstone
chmod +x ./make.sh
./make.sh
sudo ./make.sh install
cd ..

# install gtirb-capstone
cd gtirb-capstone
pip install wheel ipython ipdb tqdm
pip install .
cd ..

# install gtirb-functions
cd gtirb-functions
pip install .
cd ..
