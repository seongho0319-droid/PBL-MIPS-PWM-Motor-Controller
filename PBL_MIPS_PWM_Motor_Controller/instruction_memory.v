`timescale 1ns / 1ps
module instruction_memory #(
    parameter WIDTH = 32,
    parameter DEPTH = 256
)(
    input  wire [31:0] addr,       // byte address
    output wire [31:0] rd          // instruction
);
    reg [WIDTH-1:0] ram [0:DEPTH-1];
    integer i;
    
    initial begin
        for (i = 0; i < DEPTH; i = i + 1)
            ram[i] = {WIDTH{1'b0}};
        $readmemh("memfile.dat", ram, 0, 8);  // load program
    end
    
    assign rd = ram[addr[31:2]];   // word aligned
endmodule
