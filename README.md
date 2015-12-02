# CS-472-Project-3
CS 472 - Computer Architecture (Taken SUMMER 2015)

Pipelined datapath simulation

OVERVIEW

This lab will be written in the language of your choice and will simulate how a pipelined datapath works. It must have a function (or procedure or method or whatever the term is for a code module in your language of choice) for each step in the pipeline: IF, ID, EX, MEM, and WB with the function names shown below. Your main program will have some initialization code and then will be one big loop, where each time through the loop is equivalent to one cycle in a pipeline.  That loop will call those five functions, print out the appropriate information (the 32 registers and both READ and WRITE versions of the four pipeline registers) and then copy the WRITE version of the pipeline registers into the READ version for use the next cycle.  

That is, your main program's loop will have the following sequence after initialization:

IF_stage();
ID_stage();
EX_stage();
MEM_stage();
WB_stage();
Print_out_everything();
Copy_write_to_read();

You must follow this order and include these exact function names for the five stages.  Projects which go in the inverse order -- starting with WB, then MEM, then EX, then ID, then IF -- will get a zero!
