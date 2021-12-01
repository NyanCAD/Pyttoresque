module blink(input clk, output led);
   
    reg [11:0] counter = 12'h0;
   
    always @(posedge clk) 
        counter <= counter + 1'b1;
   
    assign led = counter[7];
   
endmodule