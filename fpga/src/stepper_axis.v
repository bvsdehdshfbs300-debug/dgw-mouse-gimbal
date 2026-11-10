module stepper_axis (
    input  wire        clk,
    input  wire        enable,
    input  wire        dir_in,
    input  wire [31:0] half_period_cycles,
    output reg         step = 1'b0,
    output reg         dir = 1'b0
);

    reg [31:0] counter = 32'd0;

    always @(posedge clk) begin
        dir <= dir_in;

        if (!enable || half_period_cycles == 32'd0) begin
            counter <= 32'd0;
            step <= 1'b0;
        end else if (counter >= half_period_cycles - 1'b1) begin
            counter <= 32'd0;
            step <= ~step;
        end else begin
            counter <= counter + 1'b1;
        end
    end
endmodule
