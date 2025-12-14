#!/bin/bash

#PBS -q {queue}

#PBS -l select=1:ncpus={ppn}:mpiprocs={ppn}:mem=8GB
#PBS -l place=scatter
#PBS -l walltime=24:00:00
#PBS -N {simulation_name}

#PBS -V
#PBS -koed

cd "$PBS_O_WORKDIR"

mpirun -np {ppn} {lammps_exe} -in box.in
