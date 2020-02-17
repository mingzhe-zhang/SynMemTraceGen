from __future__ import division
import sys
import os
import time
import math
import re
import argparse
import random
import numpy as py

def init_trace(trace_buf, args):
	trace_length = args.trace_length
	read_proportion = args.read_proportion
	if read_proportion == 0: # all write
		for _ in range(0, trace_length):
			trace_buf.append([0,"W"])
	elif read_proportion == 1: # all read
		for _ in range(0, trace_length):
			trace_buf.append([0,"R"])
	elif read_proportion < 1 and read_proportion > 0:
		read_count = int(trace_length * read_proportion)
		write_count = trace_length - read_count
		trace_buf = [[0] for _ in range(0, trace_length)]
		all_seq = [i for i in range(0, trace_length)]
		read_seq = random.sample(all_seq, read_count)
		#read_seq.sort()
		#write_seq = all_seq - read_seq
		for idx in read_seq:
			#trace_buf[idx].append(0)
			trace_buf[idx].append("R")
		for idx in range(0, trace_length):
			if len(trace_buf[idx]) == 1:
				#trace_buf[idx].append(0)
				trace_buf[idx].append("W")
	return trace_buf

def spatial_pattern_gen(trace_buf, args):
	pattern_type = args.spatial_pattern_type
	addr_seq_length = len(trace_buf)
	if pattern_type == "random":
		addr_seq = [int(random.uniform(0, args.capacity * 1024 * 1024 * 1024 /(args.system_type/8))) for _ in range(0, addr_seq_length)]
		for idx in range(0, addr_seq_length):
			trace_buf[idx].append(str(hex(addr_seq[idx]*8)))
	elif pattern_type == "sequential":
		end_point = args.capacity * 1024 * 1024 * 1024 / (args.system_type/8)
		cur_point = random.randint(0, end_point)
		for idx in range(0, addr_seq_length):
			if cur_point < end_point:
				trace_buf[idx].append(str(hex(cur_point*8)))
				cur_point = cur_point + 1
			else:
				cur_point = random.randint(0, end_point)
	else:
		print("Un-supported spatial pattern! Exit.\n")
		exit(1)
	return trace_buf

def temporal_pattern_gen(trace_buf, args):
	pattern_type = args.temporal_pattern_type
	access_per_window = args.mpki * args.period_width / 1000
	access_for_intensive = access_per_window * args.intensive_proportion
	access_for_non_intensive = access_per_window - access_for_intensive
	avg_interval_for_intensive = args.period_width * args.busy_phase_proportion / access_for_intensive
	avg_interval_for_non_intensive = args.period_width * (1-args.busy_phase_proportion) / access_for_non_intensive
	time_seq_intensive = []
	time_seq_non_intensive = []
	served_access = 0
	while served_access < args.trace_length:
		if args.trace_length - served_access < access_per_window:
			access_per_window = args.trace_length - served_access
			access_for_intensive = access_per_window * args.intensive_proportion
			access_for_non_intensive = access_per_window - access_for_intensive
			avg_interval_for_intensive = args.period_width * args.busy_phase_proportion / access_for_intensive
			avg_interval_for_non_intensive = args.period_width * (1-args.busy_phase_proportion) / access_for_non_intensive
		if pattern_type == "uniform":
			time_seq_intensive = py.random.uniform(low=0, high=avg_interval_for_intensive, size=access_for_intensive)
			time_seq_non_intensive = py.random.uniform(low=0, high=avg_interval_for_non_intensive, size=access_for_non_intensive)
		elif pattern_type == "poisson":
			time_seq_intensive = py.random.poisson(lam=avg_interval_for_intensive, size=access_for_intensive)
			time_seq_non_intensive = py.random.poisson(lam=avg_interval_for_non_intensive, size=access_for_non_intensive)
		#time_seq = time_seq_intensive + time_seq_non_intensive
		else:
			print("Un-supported temporal pattern! Exit.\n")
			exit(1)
		for idx in range(0, int(access_per_window)):
			if idx < len(time_seq_intensive):
				#print("len(trace_buf)="+str(len(trace_buf))+", served_access+idx="+str(served_access+idx)+", len(time_seq_intensive)="+str(len(time_seq_intensive))+", idx="+str(idx)+"\n")
				trace_buf[served_access + idx][0]=int(time_seq_intensive[idx])
			else:
				trace_buf[served_access + idx][0]=int(time_seq_non_intensive[idx-len(time_seq_intensive)])
		served_access += int(access_per_window)
	return trace_buf

def trace_finish(trace_buf, args):
	total_read = args.trace_length * args.read_proportion
	#inst_width = args.system_type / 8
	pc_seq = py.random.uniform(low=1, high=args.pc_max_interval, size=total_read)
	pc_idx = 0
	pc_cur = random.randint(0, 1000)
	for idx in range(0, args.trace_length):
		if trace_buf[idx][1] == "R":
			trace_buf[idx].append(str(hex(int((pc_cur+pc_seq[pc_idx])*8))))
			pc_cur += pc_seq[pc_idx]
			pc_idx += 1
	return trace_buf

def trace_output(trace_buf, args):
	output_file=open(args.output_filename, 'w')
	output_buf=[]
	for line in trace_buf:
		temp_str=""
		for item in line:
			temp_str += str(item)+" "
		output_buf.append(temp_str+"\n")
	output_file.writelines(output_buf)
	output_file.close()


parser = argparse.ArgumentParser()
parser.add_argument("-mpki", help="Memory Access Per Kilo Instructions.",
	type=float, dest="mpki", default = 1.0)
parser.add_argument("-p", help="Periodic Window Width. (in instructions number)", 
	type=int, dest="period_width", default = 10000)
parser.add_argument("-b", help="Busy phase proportion in each periodic window.", 
	type=float, dest="busy_phase_proportion", default = 0.2)
parser.add_argument("-ip", help="Intensive Proportion (The proportion of the memory access in the busy phase for each periodic window).",
	type=float, dest="intensive_proportion", default = 0.8)
parser.add_argument("-rp", help="Read Request Proportion",
	type=float, dest="read_proportion", default = 0.5)
parser.add_argument("-n", help="The length of the output trace (in the number of memory accesses).", 
	type=int, dest="trace_length", default = 1000000)
parser.add_argument("-o", help="The output filename.", 
	type=str, dest="output_filename", default = "out.tr")
parser.add_argument("-st", help="Memory Spartial Pattern Type (sequential|random|strided|linear|neighbor|2d-spartial|scatter|gather|combine-scatter-gather)",
	type=str, dest="spatial_pattern_type", default = "random")
parser.add_argument("-tt", help="Memory Temporal Pattern Type (uniform|poisson)",
	type=str, dest="temporal_pattern_type", default = "uniform")
parser.add_argument("-m", help="Memory Capacity (GB)",
	type=int, dest="capacity", default = 4)
parser.add_argument("-c", help="Cacheline Size (B)",
	type=int, dest="cacheline_size", default =64)
parser.add_argument("-s", help="System Type (32bit/64bit)",
	type=int, dest="system_type", default = 64)
parser.add_argument("-is", help="PC max interval", 
	type=int, dest="pc_max_interval", default = 50)
args = parser.parse_args()


trace_buf = []
trace_buf=init_trace(trace_buf, args)
print("init finish.\n")
trace_buf=spatial_pattern_gen(trace_buf, args)
print("spatial pattern generation finish.\n")
trace_buf=temporal_pattern_gen(trace_buf, args)
print("temporal pattern generation finish.\n")
trace_buf=trace_finish(trace_buf, args)
print("trace finish.\n")
trace_output(trace_buf, args)
print("output finish.\n")



