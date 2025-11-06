#!/bin/bash
#PBS -N {simulation_name}
#PBS -l nodes={node}:ppn={ppn}
#PBS -q {queue}
#PBS -l mem=4gb
#PBS -l walltime=03:00:00
cd "$PBS_O_WORKDIR"

mpirun -np {ppn} {lammps_exe} -in box.in
