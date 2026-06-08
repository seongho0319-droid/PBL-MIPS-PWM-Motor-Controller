`timescale 1ns / 1ps

module mips_tb;
    reg         clk;
    reg         rst_n;
    reg  [7:0]  switches;

    wire        pwm_out;
    wire [31:0] pc_out;
    wire [31:0] alu_result;
    wire [7:0]  pwm_duty_out;
    wire        pwm_en_out;
    wire        mmio_write;
    wire [31:0] mmio_addr;
    wire [31:0] mmio_write_data;
    reg  [7:0]  last_logged_duty;
    reg         duty_log_valid;

    mips uut (
        .clk(clk),
        .rst_n(rst_n),
        .switches(switches),
        .pwm_out(pwm_out),
        .pc_out(pc_out),
        .alu_result(alu_result)
    );

    // GTKWave-friendly aliases matching the assignment wording.
    assign pwm_duty_out = uut.u_datapath.u_data_mem.pwm_duty;
    assign pwm_en_out = uut.u_datapath.u_data_mem.pwm_en;
    assign mmio_write = uut.u_datapath.mem_write_M;
    assign mmio_addr = uut.u_datapath.alu_result_M_reg;
    assign mmio_write_data = uut.u_datapath.write_data_M;

    initial begin
        clk = 1'b0;
        forever #5 clk = ~clk;
    end

    initial begin
        $dumpfile("wave.vcd");
        $dumpvars(0, mips_tb);
    end

    initial begin
        rst_n = 1'b0;
        switches = 8'h00;
        last_logged_duty = 8'h00;
        duty_log_valid = 1'b0;
        #25;
        rst_n = 1'b1;

        $display("PBL MIPS PWM Motor Controller simulation");

        #20000 switches = 8'h40;
        $display("%0t switches set to %h", $time, switches);
        #25000 switches = 8'h80;
        $display("%0t switches set to %h", $time, switches);
        #25000 switches = 8'hC0;
        $display("%0t switches set to %h", $time, switches);
        #25000 switches = 8'hFF;
        $display("%0t switches set to %h", $time, switches);
        #25000 switches = 8'h00;
        $display("%0t switches set to %h", $time, switches);
        #15000;

        $display("Simulation complete. Inspect wave.vcd for PWM duty changes.");
        $finish;
    end

    always @(posedge clk) begin
        if (rst_n && uut.u_datapath.mem_write_M) begin
            if (uut.u_datapath.alu_result_M_reg == 32'h00000098) begin
                if (!duty_log_valid || (uut.u_datapath.write_data_M[7:0] != last_logged_duty)) begin
                    $display("%0t PWM duty write <= %h", $time, uut.u_datapath.write_data_M[7:0]);
                    last_logged_duty <= uut.u_datapath.write_data_M[7:0];
                    duty_log_valid <= 1'b1;
                end
            end else if (uut.u_datapath.alu_result_M_reg == 32'h0000009C) begin
                $display("%0t PWM enable write <= %b", $time, uut.u_datapath.write_data_M[0]);
            end
        end
    end
endmodule
