//==============================================================================
// Data Memory with MMIO (Memory-Mapped I/O)
//==============================================================================
// Description:
// Standard RAM for data storage, plus memory-mapped registers for I/O.
// 
// Address Map:
// - 0x000+       : Internal RAM
// - 0x090        : Switches input (read-only)
// - 0x098        : PWM duty register (write-only)
// - 0x09C        : PWM enable register (write-only)
//==============================================================================
`timescale 1ns / 1ps

module data_memory (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        mem_write_en,
    input  wire [31:0] addr,
    input  wire [31:0] write_data,
    input  wire [7:0]  switches,

    output wire        pwm_out,

    output reg  [31:0] read_data
);
    localparam [31:0] SWITCH_ADDR = 32'h00000090;
    localparam [31:0] PWM_DUTY_ADDR = 32'h00000098;
    localparam [31:0] PWM_EN_ADDR   = 32'h0000009C;

    reg [31:0] ram [0:63];
    wire [31:0] ram_out;
    assign ram_out = ram[addr[7:2]];

    reg [7:0] pwm_duty;
    reg       pwm_en;

    pwm_controller u_pwm (
        .clk(clk),
        .rst_n(rst_n),
        .en(pwm_en),
        .duty(pwm_duty),
        .pwm_out(pwm_out)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pwm_duty <= 8'd0;
            pwm_en <= 1'b0;
        end else if (mem_write_en) begin
            case (addr)
                SWITCH_ADDR:   ; // Read-only: writes are ignored.
                PWM_DUTY_ADDR: pwm_duty <= write_data[7:0];
                PWM_EN_ADDR:   pwm_en <= write_data[0];
                default:       ram[addr[7:2]] <= write_data;
            endcase
        end
    end

    always @(*) begin
        case (addr)
            SWITCH_ADDR:   read_data = {24'b0, switches};
            PWM_DUTY_ADDR: read_data = 32'd0;
            PWM_EN_ADDR:   read_data = 32'd0;
            default:       read_data = ram_out;
        endcase
    end

    integer i;
    initial begin
        pwm_duty = 8'd0;
        pwm_en = 1'b0;
        for (i = 0; i < 64; i = i + 1)
            ram[i] = 32'd0;
    end

endmodule
