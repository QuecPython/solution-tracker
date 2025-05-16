import utime
from usr.libs.i2c import I2CIOWrapper


#i2c address
LPS22HB_SLAVE_ADDRESS	  =  0x5C
# id
LPS22HB_CHIP_ID       =  0xB1

#Register 
LPS_INT_CFG           =  b"\x0B"  # Interrupt register
LPS_THS_P_L           =  b"\x0C"  # Pressure threshold registers
LPS_THS_P_H           =  b"\x0D"        
LPS_WHO_AM_I          =  b"\x0F"  # Who am I
LPS_CTRL_REG1         =  b"\x10"  # Control registers
LPS_CTRL_REG2         =  b"\x11"
LPS_CTRL_REG3         =  b"\x12"
LPS_FIFO_CTRL         =  b"\x14"  # FIFO configuration register 
LPS_REF_P_XL          =  b"\x15"  # Reference pressure registers
LPS_REF_P_L           =  b"\x16"
LPS_REF_P_H           =  b"\x17"
LPS_RPDS_L            =  b"\x18"  # Pressure offset registers
LPS_RPDS_H            =  b"\x19"        
LPS_RES_CONF          =  b"\x1A"  # Resolution register
LPS_INT_SOURCE        =  b"\x25"  # Interrupt register
LPS_FIFO_STATUS       =  b"\x26"  # FIFO status register
LPS_STATUS            =  b"\x27"  # Status register
LPS_PRESS_OUT_XL      =  b"\x28"  # Pressure output registers
LPS_PRESS_OUT_L       =  b"\x29"
LPS_PRESS_OUT_H       =  b"\x2A"
LPS_TEMP_OUT_L        =  b"\x2B"  # Temperature output registers
LPS_TEMP_OUT_H        =  b"\x2C"
LPS_RES               =  b"\x33"  # Filter reset register


class Lps22hb(I2CIOWrapper):

    def init(self):
        chip_id = self.getChipId()
        if chip_id != LPS22HB_CHIP_ID:
            raise ValueError("{} got Wrong chip id: 0x{:02X}".format(type(self).__name__, chip_id))
        self.reset()  # Wait for reset to complete
        self.write(LPS_CTRL_REG1, b"\x02")  # Low-pass filter disabled , output registers not updated until MSB and LSB have been read , Enable Block Data Update , Set Output Data Rate to 0 

    def getChipId(self):
        return self.read(LPS_WHO_AM_I)[0]

    def reset(self):
        data = self.read(LPS_CTRL_REG2)[0]
        data |= 0x04
        self.write(LPS_CTRL_REG2, bytes([data]))  # SWRESET Set 1
        while data:
            data = self.read(LPS_CTRL_REG2)[0]
            data &= 0x04

    def __startOneshot(self):
        data = self.read(LPS_CTRL_REG3)[0]
        data = self.read(LPS_CTRL_REG2)[0]
        data |= 0x01  # ONE_SHOT Set 1
        self.write(LPS_CTRL_REG2, bytes([data]))

    def getTempAndPressure(self):
        self.__startOneshot()
        for _ in range(10):
            status = self.read(LPS_STATUS)[0]
            if not (status & 0x01 and status & 0x02):
                continue
            press_out_xl = self.read(LPS_PRESS_OUT_XL)[0]
            press_out_l = self.read(LPS_PRESS_OUT_L)[0]
            press_out_h = self.read(LPS_PRESS_OUT_H)[0]
            press_data = ((press_out_h << 16) + (press_out_l << 8) + press_out_xl) / 4096.0
            temp_out_l = self.read(LPS_TEMP_OUT_L)[0]
            temp_out_h = self.read(LPS_TEMP_OUT_H)[0]
            temp_data =((temp_out_h << 8) + temp_out_l) / 100.0
            return round(press_data, 2), round(temp_data, 2)
        else:
            return 0, 0
        

if __name__ == '__main__':
    print("\nPressure Sensor Test Program ...\n")
    from machine import I2C

    lps22hb=Lps22hb(I2C(I2C.I2C1, I2C.STANDARD_MODE), LPS22HB_SLAVE_ADDRESS)
    lps22hb.init()
    
    for i in range(100):
        try:
            press_data, temp_data = lps22hb.getTempAndPressure()
            utime.sleep_ms(100)
            print('Pressure: {:6.2f} hPa, Temperature: {:6.2f} °C'.format(press_data or 0, temp_data or 0))
        except Exception as e:
            print(e) 
            break 
