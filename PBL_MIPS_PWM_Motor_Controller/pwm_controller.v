`timescale 1ns / 1ps

module pwm_controller (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       en,
    input  wire [7:0] duty,
    output wire       pwm_out
);
    reg [7:0] counter;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            counter <= 8'd0;
        else
            counter <= counter + 8'd1;
    end

    assign pwm_out = en && (counter < duty);
endmodule
