# PBL MIPS PWM Motor Controller

Complete pipelined MIPS processor extended with memory-mapped PWM output for switch-controlled motor speed.

## System Diagram

```text
+----------+      +-------------+      +----------------+      +---------+
| MIPS CPU | ---> | Data Memory | ---> | PWM Controller | ---> | pwm_out |
| pipeline |      | MMIO decode |      | 8-bit counter  |      | motor   |
+----------+      +-------------+      +----------------+      +---------+
                       ^
                       |
                  switches[7:0]
```

## MMIO Address Map

| Address | Access | Function |
| --- | --- | --- |
| `0x0000+` | read/write | Normal RAM |
| `0x0090` | read-only | Zero-extended 8-bit switches: `{24'b0, switches}` |
| `0x0098` | write-only | PWM duty register, stores `write_data[7:0]` |
| `0x009C` | write-only | PWM enable register, stores `write_data[0]` |

## Commands

```text
make
gtkwave wave.vcd
```

## Python Waveform Plot Check

Run the simulation first, then generate a PNG summary plot from `wave.vcd`.

```text
make
python -m pip install matplotlib
python scripts/plot_waveform.py
python scripts/plot_waveform.py --show
```

The default output is `docs/waveform_profile.png`. You can also choose a VCD explicitly:

```text
python scripts/plot_waveform.py --vcd wave.vcd
```

## Expected Waveform Behavior

After reset, the program writes `1` to `0x009C`, enabling PWM. It then loops forever, reading `switches` from `0x0090` and writing that value to `0x0098`. In the waveform, `pwm_en_out` should become `1`, `pwm_duty_out` should follow the testbench switch values, and `pwm_out` should have a wider high pulse as duty changes from `8'h00` to `8'h40`, `8'h80`, `8'hC0`, and `8'hFF`.

Useful GTKWave signals:

```text
mips_tb.switches
mips_tb.pwm_out
mips_tb.pc_out
mips_tb.pwm_duty_out
mips_tb.pwm_en_out
mips_tb.uut.u_datapath.mem_write_M
mips_tb.uut.u_datapath.alu_result_M_reg
mips_tb.uut.u_datapath.write_data_M
```

## File Layout

```text
PBL_MIPS_PWM_Motor_Controller/
|-- README.md
|-- Makefile
|-- memfile.dat
|-- program.asm
|-- scripts/
|   `-- plot_waveform.py
|-- mips.v
|-- mips_tb.v
|-- datapath.v
|-- data_memory.v
|-- pwm_controller.v
|-- alu.v
|-- alu_decoder.v
|-- control_unit.v
|-- hazard_unit.v
|-- instruction_memory.v
|-- main_decoder.v
|-- pc.v
|-- reg_file.v
`-- docs/
    |-- design_report.md
    |-- test_report.md
    `-- waveform_profile.png
```
