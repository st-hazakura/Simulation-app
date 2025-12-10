#!/bin/bash
#PBS -N {simulation_name}
#PBS -l nodes={node}:ppn={ppn}
#PBS -q {queue}
#PBS -l mem=8gb
#PBS -l walltime=24:00:00
cd "$PBS_O_WORKDIR"

mpirun -np {ppn} {lammps_exe} -in box.in
