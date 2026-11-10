module mouse_gimbal_top (
    input  wire clk,
    input  wire uart_rx,
    output wire uart_tx,
    output wire m1_step,
    output wire m1_dir,
    output wire m1_en,
    output wire m2_step,
    output wire m2_dir,
    output wire m2_en,
    output reg  status_led = 1'b0
);

    localparam integer CLK_HZ = 50_000_000;
    localparam integer BAUD = 115200;
    localparam integer CLKS_PER_BIT = CLK_HZ / BAUD;

    wire rx_valid;
    wire [7:0] rx_byte;

    uart_rx #(
        .CLKS_PER_BIT(CLKS_PER_BIT)
    ) u_uart_rx (
        .clk(clk),
        .rx(uart_rx),
        .data_valid(rx_valid),
        .data(rx_byte)
    );

    reg [3:0] parser_index = 4'd0;
    reg [7:0] frame [0:10];
    reg [7:0] checksum = 8'd0;

    reg x_enable = 1'b0;
    reg y_enable = 1'b0;
    reg x_dir = 1'b0;
    reg y_dir = 1'b0;
    reg [31:0] x_half_period = 32'd0;
    reg [31:0] y_half_period = 32'd0;

    assign uart_tx = 1'b1;

    always @(posedge clk) begin
        if (rx_valid) begin
            if (parser_index == 4'd0) begin
                if (rx_byte == 8'hA5) begin
                    frame[0] <= rx_byte;
                    checksum <= rx_byte;
                    parser_index <= 4'd1;
                end
            end else begin
                frame[parser_index] <= rx_byte;

                if (parser_index < 4'd10) begin
                    checksum <= checksum ^ rx_byte;
                    parser_index <= parser_index + 1'b1;
                end else begin
                    if (rx_byte == checksum) begin
                        x_enable <= frame[1][0];
                        x_dir <= frame[1][1];
                        y_enable <= frame[1][2];
                        y_dir <= frame[1][3];

                        x_half_period <= {frame[2], frame[3], frame[4], frame[5]};
                        y_half_period <= {frame[6], frame[7], frame[8], frame[9]};
                        status_led <= ~status_led;
                    end
                    parser_index <= 4'd0;
                    checksum <= 8'd0;
                end
            end
        end
    end

    stepper_axis u_x_axis (
        .clk(clk),
        .enable(x_enable),
        .dir_in(x_dir),
        .half_period_cycles(x_half_period),
        .step(m1_step),
        .dir(m1_dir)
    );

    stepper_axis u_y_axis (
        .clk(clk),
        .enable(y_enable),
        .dir_in(y_dir),
        .half_period_cycles(y_half_period),
        .step(m2_step),
        .dir(m2_dir)
    );

    assign m1_en = x_enable;
    assign m2_en = y_enable;
endmodule
