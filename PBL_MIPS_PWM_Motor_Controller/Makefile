# PBL MIPS PWM Motor Controller

SRC = mips.v control_unit.v hazard_unit.v \
      main_decoder.v alu_decoder.v \
      datapath.v pc.v instruction_memory.v \
      reg_file.v alu.v data_memory.v \
      pwm_controller.v

TB  = mips_tb.v
OUT = sim.out
VCD = wave.vcd

all: compile run

compile:
	iverilog -Wall -o $(OUT) $(TB) $(SRC)

run:
	vvp -n $(OUT)

wave: all
	gtkwave $(VCD)

clean:
	if exist $(OUT) del $(OUT)
	if exist $(VCD) del $(VCD)
