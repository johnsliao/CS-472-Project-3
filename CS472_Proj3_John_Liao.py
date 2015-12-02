## John Liao
## CS 472 SUMMER
## Project #3
## main.py

import copy
import sys

def parse_bits_26_31(instruction):
    return instruction & 0xFC000000

def parse_bits_21_25(instruction):
    return instruction & 0x3E00000

def parse_bits_16_20(instruction):
    return instruction & 0x1F0000

def parse_bits_11_15(instruction):
    return instruction & 0xF800

def parse_bits_0_5(instruction):
    return instruction & 0x3F

def parse_bits_0_15(instruction):
    return instruction & 0xFFFF

def twos_comp(val):
    if val >> 15 == 1: # if signed bit is set
        val -= 2**16 # convert value as signed *int* [val - 2^16]
    return val # else return as normal

# ------------------------- PIPELINE REGISTERS ------------------------- #

class IF_ID:

    def __init__(self, instruction, incrPC):
        self.instruction = instruction
        self.incrPC = incrPC

class ID_EX:

    def __init__(self):
        self.instruction = 0x0

        # Controls
        self.RegDST = 0
        self.ALUSrc = 0
        self.ALUOp = 0
        self.MemRead = 0
        self.MemWrite = 0
        self.Branch = 0
        self.MemToReg = 0
        self.RegWrite = 0

        self.SEOffset = 0
        self.incrPC = 0

        self.ReadReg1Value = 0
        self.ReadReg2Value = 0

        self.WriteReg_20_16 = 0
        self.WriteReg_15_11 = 0

        self.Func = 0x0
        self.opcode = 0x0


    def instruction_decode(self, instruction, incrPC):
        self.instruction = instruction
        self.incrPC = incrPC

        opcode = parse_bits_26_31(instruction) >> 26
        self.opcode = opcode

        if opcode == 0: # R format
            src1 = parse_bits_21_25(instruction)
            src2 = parse_bits_16_20(instruction)
            dest = parse_bits_11_15(instruction)
            # disregard bits 6-10...
            func = parse_bits_0_5(instruction)

            if func == 32 or func == 34: #add/sub

                self.RegDST = 1
                self.ALUSrc = 0
                self.MemToReg = 0
                self.RegWrite = 1
                self.MemRead = 0
                self.MemWrite = 0
                self.Branch = 0
                self.ALUOp = 0b10

                if func == 32:
                    self.Func = 0x20
                if func == 34:
                    self.Func = 0x22

                self.WriteReg_20_16 = str(src2>>16)
                self.WriteReg_15_11 = str(dest>>11)

                self.ReadReg1Value = Regs[src1>>21]
                self.ReadReg2Value = Regs[src2>>16]

                self.SEOffset = -999 # garbage

        else: # I FORMAT
            src1 = parse_bits_21_25(instruction)
            dest = parse_bits_16_20(instruction)
            offset = parse_bits_0_15(instruction)

            if opcode == 32: #lb
                self.RegDST = 0
                self.ALUSrc = 1
                self.MemToReg = 1
                self.RegWrite = 1
                self.MemRead = 1
                self.MemWrite = 0
                self.Branch = 0
                self.ALUOp = 0b00

                self.WriteReg_20_16 = str(dest>>16)
                self.WriteReg_15_11 = 0

                self.ReadReg1Value = Regs[src1>>21]
                self.ReadReg2Value = Regs[dest>>16]

                self.Func = -999 # garbage

                self.SEOffset = twos_comp(offset)

            elif opcode == 40: #sb
                self.RegDST = -999 # garbage
                self.ALUSrc = 1
                self.MemToReg = -999 # garbage
                self.RegWrite = 0
                self.MemRead = 0
                self.MemWrite = 1
                self.Branch = 0
                self.ALUOp = 0b00

                self.Func = -999 # garbage

                self.WriteReg_20_16 = str(dest>>16)
                self.WriteReg_15_11 = 0

                self.ReadReg1Value = Regs[src1>>21]
                self.ReadReg2Value = Regs[dest>>16]

                self.SEOffset = twos_comp(offset)


    def reset(self):
        self.RegDST = 0
        self.ALUSrc = 0
        self.ALUOp = 0
        self.MemRead = 0
        self.MemWrite = 0
        self.Branch = 0
        self.MemToReg = 0
        self.RegWrite = 0

        self.SEOffset = 0
        self.incrPC = 0

        self.ReadReg1Value = 0
        self.ReadReg2Value = 0

        self.WriteReg_15_11 = 0
        self.WriteReg_20_16 = 0

        self.WriteReg1 = 0
        self.WriteReg2 = 0

        self.Func = 0x0

class EX_MEM:

    def __init__(self):
        self.MemRead = 0
        self.MemWrite = 0
        self.Branch = 0
        self.MemToReg = 0
        self.RegWrite = 0

        self.ReadReg1Value = 0
        self.ReadReg2Value = 0

        self.SEOffset = 0

        self.ALUOp = 0

        self.incrPC = 0

        # Specific to Execute stage
        self.CalcBTA = -999
        self.Zero = 0
        self.ALUResult = 0
        self.SWValue = 0
        self.WriteRegNum = 0

    def execute(self, MemRead, MemWrite, Branch, RegWrite,
                ALUOp, ReadReg1Value, ReadReg2Value, SEOffset,
                Func, IncrPC, opcode, RegDST,
                WriteReg_20_16, WriteReg_15_11, MemToReg, incrPC):
        self.MemRead = MemRead
        self.MemWrite = MemWrite
        self.MemToReg = MemToReg
        self.RegWrite = RegWrite
        self.Branch = Branch
        self.incrPC =incrPC

        self.CalcBTA = self.calculate_BTA(SEOffset, IncrPC)
        
        if RegDST == 1: # r
            self.WriteRegNum = WriteReg_15_11
        elif RegDST == 0: # load
            self.WriteRegNum = WriteReg_20_16
        else: # stores
            self.WriteRegNum = -999 # garbage

        if ALUOp == 0b10: # R Instruction
            if Func == 32: # add
                self.ALUResult = ReadReg1Value + ReadReg2Value
                self.SWValue = ReadReg2Value
            elif Func == 34: # sub
                self.ALUResult = ReadReg1Value - ReadReg2Value
                self.SWValue = ReadReg2Value

        if ALUOp == 0b00: # I instruction
            if opcode == 0x20: # lb
                self.ALUResult = ReadReg1Value + SEOffset
                self.SWValue = ReadReg2Value
            elif opcode == 0x28: # sb
                self.ALUResult = ReadReg1Value + SEOffset
                self.SWValue = ReadReg2Value

    def reset(self):
        self.MemRead = 0
        self.MemWrite = 0
        self.Branch = 0
        self.MemToReg = 0
        self.RegWrite = 0
        self.ReadReg1Value = 0
        self.ReadReg2Value = 0
        self.WriteReg1 = 0
        self.WriteReg2 = 0
        self.SEOffset = 0
        self.ALUOp = 0
        self.incrPC = 0
        self.CalcBTA = -999
        self.Zero = 0
        self.ALUResult = 0
        self.SWValue = 0
        self.WriteRegNum = 0
        self.Func = 0

    def calculate_BTA(self, SEOffset, IncrPC):
        BTA = 'X'

        # sign extend the 16 bit offset value to preserve its value
        # multiply resulting value by 4
        # Add to PC + 4

        return BTA
        

class MEM_WB:

    def __init__(self):
        self.MemToReg = 0
        self.RegWrite = 0
        self.MemRead = 0
        self.MemWrite = 0
        self.Branch = 0
        self.RegWrite = 0

        self.LWDataValue = 0
        self.SWDataValue = 0
        self.ALUResult = 0
        self.WriteRegNum = 0


    def access_memory(self, MemToReg, RegWrite, ALUResult, WriteRegNum, MemRead, SWValue, MemWrite):
        self.MemToReg = MemToReg
        self.RegWrite = RegWrite
        self.ALUResult = ALUResult
        self.WriteRegNum = WriteRegNum
        self.SWDataValue = SWValue

        if MemRead == 1: # load
            self.LWDataValue = Main_Mem[ALUResult]
        elif MemWrite == 1: #store
            Main_Mem[ALUResult] = SWValue
        else: # R type, bypass Mem Stage
            pass

    def write_back(self):
        global Regs

        if self.WriteRegNum != -999:
            if self.MemWrite == 0 and self.MemToReg == 0: # r
                Regs[int(self.WriteRegNum)] = self.ALUResult

            elif self.MemWrite == 0 and self.MemToReg == 1: #lb
                self.LWDataValue = Main_Mem[self.ALUResult]
                Regs[int(self.WriteRegNum)] = self.LWDataValue


    def reset(self):
        self.MemToReg = 0
        self.RegWrite = 0
        self.MemRead = 0
        self.MemWrite = 0
        self.Branch = 0
        self.RegWrite = 0
        self.LWDataValue = 0
        self.SWDataValue = 0
        self.ALUResult = 0
        self.WriteRegNum = 0

# ------------------------- PRINT FUNCTIONS ------------------------- #

def check_garbage_val(val):

    if val == -999: # garbage value
        return 'X'
    elif val == "0xfc19": # 0xfc19 = twos complement representation of hex -999
        return 'X'
    else:
        return val

def print_main_mem(main_mem):
    for x, y in enumerate(main_mem):
        print '[', hex(x), '] = ', hex(y)

def Print_out_everything():
    print '\nREGISTERS'

    for regNum, reg in enumerate(Regs):
        print '[\t$'+ str(regNum), '=', hex(reg),'   \t]\t\t',
        if (regNum+1) % 4 == 0:
            print ''

    print '\n----------------------------------------------------------------------------------------------------'
    print '<IF/ID Write (written to by the IF stage)>'

    if IF_ID_WRITE.instruction == 0:
        print '\tControl = 00000000'
    else:
        print '\tInstruction =', hex(IF_ID_WRITE.instruction)
        print '\tIncrPC =', hex(IF_ID_WRITE.incrPC)

    print '\n<IF/ID Read (read to by the ID stage)>'
    if IF_ID_READ.instruction == 0:
        print '\tControl = 00000000'
    else:
        print '\tInstruction =', hex(IF_ID_READ.instruction)
        print '\tIncrPC =', hex(IF_ID_READ.incrPC)

    print '----------------------------------------------------------------------------------------------------'

    print '<ID/EX Write (written to by the ID stage)>'
    print '\tControl: RegDST =', check_garbage_val(ID_EX_WRITE.RegDST), 'ALUSrc =', ID_EX_WRITE.ALUSrc, \
        'ALUOp =', bin(ID_EX_WRITE.ALUOp), 'MemRead =', ID_EX_WRITE.MemRead, \
        'MemWrite =', ID_EX_WRITE.MemWrite, 'Branch =', ID_EX_WRITE.Branch, \
        'MemToReg =', check_garbage_val(ID_EX_WRITE.MemToReg), 'RegWrite =', ID_EX_WRITE.RegWrite

    if ID_EX_WRITE.instruction == 0:
        print '\n\tIncrPC = 0'
    else:
        print '\n\tIncrPC=', hex(ID_EX_WRITE.incrPC)
    
    print '\tReadReg1Value =', hex(ID_EX_WRITE.ReadReg1Value)
    print '\tReadReg2Value =', hex(ID_EX_WRITE.ReadReg2Value)

    print '\n\tSEOffset =', check_garbage_val(hex(((abs(ID_EX_WRITE.SEOffset) ^ 0xffff) + 1) & 0xffff))
    print '\tWriteReg_20_16 =', ID_EX_WRITE.WriteReg_20_16
    print '\tWriteReg_15_11 =', ID_EX_WRITE.WriteReg_15_11
    print '\tFunction =', check_garbage_val(ID_EX_WRITE.Func)


    print '\n<ID/EX Read (read to by the EX stage)>'
    print '\tControl: RegDST =', check_garbage_val(ID_EX_READ.RegDST), 'ALUSrc =', ID_EX_READ.ALUSrc, \
        'ALUOp =', bin(ID_EX_READ.ALUOp), 'MemRead =', ID_EX_READ.MemRead, \
        'MemWrite =', ID_EX_READ.MemWrite, 'Branch =', ID_EX_READ.Branch, \
        'MemToReg =', check_garbage_val(ID_EX_READ.MemToReg), 'RegWrite =', ID_EX_READ.RegWrite

    if ID_EX_READ.instruction == 0:
        print '\n\tIncrPC = 0'
    else:
        print '\n\tIncrPC=', hex(ID_EX_READ.incrPC)
        
    print '\tReadReg1Value =', hex(ID_EX_READ.ReadReg1Value)
    print '\tReadReg2Value =', hex(ID_EX_READ.ReadReg2Value)

    print '\n\tSEOffset =', check_garbage_val(hex(((abs(ID_EX_READ.SEOffset) ^ 0xffff) + 1) & 0xffff))
    print '\tWriteReg_20_16 =', ID_EX_READ.WriteReg_20_16
    print '\tWriteReg_15_11 =', ID_EX_READ.WriteReg_15_11
    print '\tFunction =', check_garbage_val(ID_EX_READ.Func)

    print '----------------------------------------------------------------------------------------------------'
    print '<EX/MEM Write (written to by the EX stage)>'
    print '\tControl: MemRead =', EX_MEM_WRITE.MemRead, 'MemWrite =', EX_MEM_WRITE.MemWrite, 'Branch =', EX_MEM_WRITE.Branch, \
        'MemToReg =', check_garbage_val(EX_MEM_WRITE.MemToReg), 'RegWrite =', EX_MEM_WRITE.RegWrite

    print '\n\tCalcBTA =', check_garbage_val(EX_MEM_WRITE.CalcBTA)
    print '\tZero =', EX_MEM_WRITE.Zero
    print '\tALUResult =', hex(EX_MEM_WRITE.ALUResult)

    print '\n\tSWValue =', hex(EX_MEM_WRITE.SWValue)
    print '\tWriteRegNum =', check_garbage_val(EX_MEM_WRITE.WriteRegNum)


    print '\n<EX/MEM READ (read to by the MEM stage)>'
    print '\tControl: MemRead =', EX_MEM_READ.MemRead, 'MemWrite =', EX_MEM_READ.MemWrite, 'Branch =', EX_MEM_READ.Branch, \
        'MemToReg =', check_garbage_val(EX_MEM_READ.MemToReg), 'RegWrite =', EX_MEM_READ.RegWrite

    print '\n\tCalcBTA =', check_garbage_val(EX_MEM_READ.CalcBTA)
    print '\tZero =', EX_MEM_READ.Zero
    print '\tALUResult =', hex(EX_MEM_READ.ALUResult)

    print '\n\tSWValue =', hex(EX_MEM_READ.SWValue)
    print '\tWriteRegNum =', check_garbage_val(EX_MEM_READ.WriteRegNum)

    print '----------------------------------------------------------------------------------------------------'
    print '<MEM/WB Write (written to by the MEM stage)>'
    print '\tControl: MemToReg =', check_garbage_val(MEM_WB_WRITE.MemToReg), 'RegWrite =', MEM_WB_WRITE.RegWrite

    print '\n\tLWDataValue =', hex(MEM_WB_WRITE.LWDataValue)
    print '\tALUResult =', hex(MEM_WB_WRITE.ALUResult)
    print '\tWriteRegNum =', check_garbage_val(MEM_WB_WRITE.WriteRegNum)

    print '\n<MEM/WB Read (read by the WB stage)>'
    print '\tControl: MemToReg = ', check_garbage_val(MEM_WB_READ.MemToReg), 'RegWrite =', MEM_WB_READ.RegWrite

    print '\n\tLWDataValue =', hex(MEM_WB_READ.LWDataValue)
    print '\tALUResult =', hex(MEM_WB_READ.ALUResult)
    print '\tWriteRegNum =', check_garbage_val(MEM_WB_READ.WriteRegNum)

    print '===================================================================================================='

def print_MM():
    print 'MAIN MEMORY'
    c = 1
    
    for index, val in enumerate(Main_Mem):
        print '[', hex(index), '] =', hex(val), '\t',

        if c > 255:
            c = 1
            print '\n\n'

        if c % 4 == 0 and c != 0 and c!= 0x100 and c != 0x200 and c!= 0x300 and c!= 0x400 and c!= 0x500 and c!= 0x600 and c!= 0x700:
            print ''


        c += 1
def Copy_write_to_read():
    global IF_ID_READ
    global ID_EX_READ
    global EX_MEM_READ
    global MEM_WB_READ

    IF_ID_READ = copy.deepcopy(IF_ID_WRITE)
    ID_EX_READ = copy.deepcopy(ID_EX_WRITE)
    EX_MEM_READ = copy.deepcopy(EX_MEM_WRITE)
    MEM_WB_READ  = copy.deepcopy(MEM_WB_WRITE)

    ID_EX_WRITE.reset() # clear values, i.e. ALU Controls, func, etc
    EX_MEM_WRITE.reset()
    MEM_WB_WRITE.reset()

# ------------------------- PIPLINE REGISTER FUNCTIONS ------------------------- #

def IF_stage(instruction, current_address):
    IF_ID_WRITE.instruction = instruction
    IF_ID_WRITE.incrPC = current_address

def ID_stage():
    ID_EX_WRITE.instruction_decode(IF_ID_READ.instruction, IF_ID_READ.incrPC)

def EX_stage():
    EX_MEM_WRITE.execute(ID_EX_READ.MemRead, ID_EX_READ.MemWrite, ID_EX_READ.Branch, ID_EX_READ.RegWrite,
                         ID_EX_READ.ALUOp, ID_EX_READ.ReadReg1Value, ID_EX_READ.ReadReg2Value, ID_EX_READ.SEOffset,
                         ID_EX_READ.Func, ID_EX_READ.incrPC, ID_EX_READ.opcode, ID_EX_READ.RegDST, ID_EX_READ.WriteReg_20_16, ID_EX_READ.WriteReg_15_11,
                         ID_EX_READ.MemToReg, ID_EX_READ.incrPC)

def MEM_stage():
    MEM_WB_WRITE.access_memory(EX_MEM_READ.MemToReg, EX_MEM_READ.RegWrite, EX_MEM_READ.ALUResult, EX_MEM_READ.WriteRegNum, EX_MEM_READ.MemRead, EX_MEM_READ.SWValue,
                               EX_MEM_READ.MemWrite)

def WB_stage():
    MEM_WB_READ.write_back()

START_ADDRESS = 0x7a000

IF_ID_WRITE = IF_ID(0x0, START_ADDRESS)
IF_ID_READ = IF_ID(0x0, 0x0)

ID_EX_WRITE = ID_EX()
ID_EX_READ = ID_EX()

EX_MEM_WRITE = EX_MEM()
EX_MEM_READ = EX_MEM()

MEM_WB_WRITE = MEM_WB()
MEM_WB_READ = MEM_WB()

Main_Mem = []
Regs = [0] * 32

def main():
    count = 0

    for x in range(0x0, 0x7FF+1):
        Main_Mem.append(count) # count goes from 0x0 to 0xFF

        count += 1

        if count > 0xFF:
            count = 0

    for x in range(0, 32):
        Regs[x] = 0x100 + x

    instructions = [0xA1020000,
                    0x810AFFFC,
                    0x00831820,
                    0x01263820,
                    0x01224820,
                    0x81180000,
                    0x81510010,
                    0x00624022,
                    0x00000000,
                    0x00000000,
                    0x00000000,
                    0x00000000]

    print '\t\t\t\t\t\t\t\t\t<< CURRENT CLOCK CYCLE: 0''>>\n' # 0th clock cycle (all NOOP)
    Print_out_everything() # clock cycle 0
    current_address = START_ADDRESS

    # MAIN LOOP
    for clockCycle in range(0,12): # 12 clock cycles
        print '\t\t\t\t\t\t\t\t\t<< CURRENT CLOCK CYCLE:', clockCycle+1,'>>\n'

        instruction = instructions[clockCycle]

        IF_stage(instruction, current_address)
        ID_stage()
        EX_stage()
        MEM_stage()
        WB_stage()
        Print_out_everything()
        Copy_write_to_read()

        current_address += 4

    print_MM()


if __name__ == '__main__':
    main()
