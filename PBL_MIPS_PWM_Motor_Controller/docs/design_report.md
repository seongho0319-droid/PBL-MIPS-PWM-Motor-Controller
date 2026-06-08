# Design Report

## Introduction

This project extends the class 13 five-stage pipelined MIPS CPU into a complete memory-mapped PWM motor controller system. The main purpose of the project is to show that a software program running on a pipelined processor can control a hardware-style output through ordinary memory access instructions. Instead of using special input/output instructions, the processor communicates with external devices through memory-mapped I/O addresses. In this design, the CPU reads an 8-bit switch input, writes that value into a PWM duty-cycle register, and the PWM controller generates a square wave whose duty cycle changes according to the switch value.

The original CPU architecture is preserved as much as possible. The datapath, control unit, hazard unit, forwarding logic, pipeline registers, and branch/jump behavior remain based on the class 13 reference design. The assignment-specific work is mainly added around the CPU rather than inside the core pipeline. The top-level module is extended to expose external switch input and PWM output ports, the data memory is extended to decode special MMIO addresses, a small PWM controller module is added, and the assembly program in `memfile.dat` controls the peripheral through `lw` and `sw` instructions. This approach keeps the CPU design stable while demonstrating how a processor can interact with a peripheral in an embedded system.

## System Architecture

The overall system can be described as a software-controlled hardware output system. The MIPS CPU executes instructions from instruction memory, performs normal pipeline execution, and uses the data-memory interface to access both ordinary RAM and special MMIO registers. When the software performs a normal memory access, the data-memory module behaves like RAM. When the software accesses one of the reserved MMIO addresses, the data-memory module routes that access to the external switch input or to the PWM control registers.

The high-level structure of the system is shown below.

```text
MIPS CPU
   |
   | lw / sw instructions
   v
Data Memory with MMIO Address Decoding
   |
   | pwm_duty / pwm_en registers
   v
PWM Controller
   |
   v
pwm_out
```

The `mips.v` module acts as the top-level CPU wrapper. It connects the existing CPU structure to the new external `switches` input and `pwm_out` output. The `datapath.v` module preserves the five-stage pipelined datapath and carries instruction and data values through the IF, ID, EX, MEM, and WB stages. The control and hazard-related modules continue to provide the normal CPU behavior, including forwarding, stalling, and branch or jump handling.

The `data_memory.v` module is the main bridge between the CPU and the peripherals. It still supports normal RAM accesses, but it also checks the address of each memory operation and redirects selected addresses to MMIO behavior. The `pwm_controller.v` module receives an enable bit and an 8-bit duty-cycle value and converts them into a PWM waveform. Finally, the `mips_tb.v` testbench provides the simulation environment, drives the switch values, runs the program, and makes it possible to inspect `pwm_out` and the internal MMIO behavior using the generated waveform.

This architecture is useful because it closely resembles how real embedded processors control hardware peripherals. The CPU does not need to know the internal implementation of the PWM controller. From the software point of view, the PWM controller is simply a set of memory addresses. By writing a value to the PWM duty address, the program changes the output waveform.

## MMIO Design

The memory-mapped I/O design is implemented in `data_memory.v`. The data-memory module keeps ordinary RAM behavior for normal addresses, but it treats a small number of specific addresses as hardware registers. This allows the existing CPU to use ordinary `lw` and `sw` instructions for hardware input and output. The program reads the switch value using `lw` from address `0x0090`, writes the PWM duty value using `sw` to address `0x0098`, and enables the PWM controller by writing to address `0x009C`.

The address map used in this project is shown below.

| Address | Device or Behavior | Direction | Notes |
| --- | --- | --- | --- |
| `0x0000+` | RAM | Read/Write | Normal data-memory access, except reserved MMIO locations |
| `0x0090` | Switches | Read-only | Returns `{24'b0, switches}` |
| `0x0098` | PWM duty register | Write-only | Stores `write_data[7:0]` into internal `pwm_duty` |
| `0x009C` | PWM enable register | Write-only | Stores `write_data[0]` into internal `pwm_en` |

The switches are treated as a read-only input device. When the CPU reads address `0x0090`, the lower 8 bits come from the external `switches` input, and the upper 24 bits are filled with zeros. This produces a 32-bit value that can be handled by the MIPS datapath. Writes to the switch address are ignored because external switches should not be modified by software.

The PWM duty register is a write-only register at address `0x0098`. Although the CPU writes a 32-bit word, only the lower 8 bits are stored in the duty register. This matches the PWM controller because the PWM controller uses an 8-bit counter and an 8-bit duty-cycle value. The PWM enable register is located at address `0x009C`, and only the lowest bit of the written data is used. When this enable bit is zero, the PWM output is forced low. When it is one, the PWM controller generates an output waveform according to the duty-cycle register.

Reads are combinational, and writes are synchronous. Combinational reads allow load instructions to receive memory or MMIO data through the normal memory-read path without requiring an additional clock edge. Synchronous writes update RAM contents and MMIO registers only on the rising clock edge. This makes register updates stable and predictable, and it prevents peripheral registers from changing in the middle of a clock cycle. This behavior is also consistent with typical hardware register design, where control registers are updated on a clock edge.

In GTKWave, the testbench provides assignment-friendly aliases:

```text
switches[7:0]
pwm_duty_out[7:0]
pwm_en_out
pwm_out
```

Internally, `pwm_duty_out` is connected to `data_memory.v`'s `pwm_duty` register, and `pwm_en_out` is connected to `data_memory.v`'s `pwm_en` register.

## PWM Controller Design

The PWM controller is implemented in `pwm_controller.v`. Its design is intentionally simple and consists of an 8-bit free-running counter and a comparator. On each clock cycle after reset, the counter increments. Because the counter is 8 bits wide, it naturally wraps around from 255 back to 0. This means that one full PWM period contains 256 clock cycles.

The PWM output is generated by comparing the current counter value with the duty register value. The basic output logic is:

```text
pwm_out = en && (counter < duty)
```

When `en` is low, `pwm_out` remains zero regardless of the duty value. When `en` is high, the output is high while the counter value is less than the duty value and low otherwise. Therefore, a larger duty value produces a longer high time during each PWM period, while a smaller duty value produces a shorter high time.

Since the counter has 256 possible values, the PWM period is:

```text
PWM period = 256 * T_clk
```

The PWM frequency is therefore:

```text
PWM frequency = f_clk / 256
```

For example, a duty value of 64 makes the output high for 64 out of 256 counter values, which is approximately a 25% duty cycle. A duty value of 128 gives approximately a 50% duty cycle. A duty value of 192 gives approximately a 75% duty cycle. A duty value of 0 keeps the output low for the entire period. A duty value of 255 keeps the output high for 255 out of 256 counts, which is almost fully high, although not exactly 100% because the comparison uses `counter < duty`.

This counter-and-comparator structure is a standard PWM implementation. It is easy to verify in simulation because the high-time of the waveform directly follows the duty register. When the software changes the duty value through the MMIO register, the pulse width of `pwm_out` changes accordingly.

## Software Algorithm

This project implements Option B, the switch-controlled duty-cycle profile. The goal of this option is to continuously read the 8-bit switch input and use that value as the PWM duty cycle. This makes the duty cycle externally controllable during simulation. Instead of following a fixed ramp or lookup table, the program responds to the current switch value.

The software first enables the PWM controller. It loads the value `1` into a register and stores that value to the PWM enable address `0x009C`. After the PWM controller is enabled, the program sets up the MMIO addresses used by the loop. The switch input address is `0x0090`, and the PWM duty register address is `0x0098`. The program then enters an infinite loop. Inside the loop, it reads the current switch value with `lw`, writes that value to the PWM duty register with `sw`, and jumps back to repeat the same process.

The software behavior can be summarized in pseudocode as follows.

```text
enable PWM

loop:
    duty = switches[7:0]
    PWM_duty_register = duty
    repeat loop
```

The important point is that the software controls the hardware using ordinary memory instructions. The `lw` instruction reads the external switch input through the MMIO address decoder, and the `sw` instruction updates the duty register inside the data-memory/MMIO module. The PWM controller does not directly read the switch input. Instead, the CPU acts as the controller that transfers the switch value into the PWM duty register.

A `nop` is placed after the jump instruction to keep the jump delay slot harmless in the reference CPU design. This avoids unintended behavior from an instruction executing immediately after the jump. The loop is intentionally simple so that the focus of the project remains on the hardware/software interaction through MMIO. Because the loop repeatedly reads the switch value, changes in the testbench-driven `switches` input eventually appear as changes in the PWM duty cycle. In GTKWave, this can be verified by observing that different switch values produce different high-time ratios on `pwm_out`.

## Verification Approach

The design is verified by running the simulation with the program loaded into `memfile.dat`. The expected behavior is that the CPU first enables the PWM controller by writing to `0x009C`. After that, it repeatedly reads from `0x0090` and writes to `0x0098`. When the testbench drives different switch values, the PWM duty register should update to match the lower 8 bits of the switch input. As the duty register changes, the width of the high portion of `pwm_out` should visibly change in the waveform.

For Option B, the most important waveform evidence is that at least three different switch values produce three different PWM duty cycles. In this testbench, the switch values are driven as:

```text
00 -> 40 -> 80 -> C0 -> FF -> 00
```

This sequence shows a clear progression from low duty to high duty and then back to zero. The waveform confirms that `pwm_duty_out[7:0]` follows `switches[7:0]`, `pwm_en_out` remains high after PWM is enabled, and `pwm_out` changes pulse width as duty increases.

The primary GTKWave signals are:

```text
clk
switches[7:0]
pwm_duty_out[7:0]
pwm_en_out
pwm_out
```

Additional MMIO debug signals are also available:

```text
mmio_write
mmio_addr[31:0]
mmio_write_data[31:0]
```

This verification confirms both sides of the system. On the software side, it confirms that the MIPS program is executing the intended loop and accessing the correct MMIO addresses. On the hardware side, it confirms that the MMIO registers update correctly and that the PWM controller converts the duty register value into the expected output waveform.

## Reflection

The safest design choice in this project was to keep the existing pipelined CPU intact and treat motor control as a memory-mapped peripheral. This avoided unnecessary changes to the datapath, forwarding logic, stall logic, and branch or jump handling. By localizing the new behavior to the top-level wiring, data-memory MMIO decoder, PWM controller, assembly program, and testbench, the design remained easier to debug and closer to the original class 13 CPU.

One part that was harder than expected was verifying the connection between the software-visible MMIO behavior and the hardware waveform. A simple change in the assembly program, address decoding, or register wiring can prevent the PWM output from changing even if the CPU itself still appears to run. Because of this, waveform inspection was important. Observing the switch input, duty register, enable register, and `pwm_out` together made it easier to confirm that the CPU was correctly controlling the peripheral.

If there were more time, one useful improvement would be to add readable PWM status registers. For example, the software could read back the current duty and enable values using `lw` instructions. This would make debugging easier and would more closely resemble real embedded peripherals, where control registers are often readable as well as writable. Another possible improvement would be to implement additional motor profiles, such as a ramp-up/ramp-down pattern or a lookup-table-based breathing pattern. However, the current Option B design successfully demonstrates the key goal of the project: a pipelined MIPS CPU can control a PWM hardware output through memory-mapped I/O.
