# PBL MIPS PWM Motor Controller - Option B
# Switch-controlled PWM duty cycle.
#
# MMIO:
#   0x0090: switches input, read-only
#   0x0098: PWM duty register, write-only
#   0x009C: PWM enable register, write-only

        addi $t0, $zero, 1       # $t0 = 1
        addi $t1, $zero, 0x009C  # $t1 = PWM enable address
        sw   $t0, 0($t1)         # enable PWM

        addi $t1, $zero, 0x0090  # $t1 = switches address
        addi $t2, $zero, 0x0098  # $t2 = PWM duty address

loop:
        lw   $t0, 0($t1)         # read zero-extended switches
        sw   $t0, 0($t2)         # write switch value as PWM duty
        j    loop                # repeat forever
        nop                      # jump delay slot
