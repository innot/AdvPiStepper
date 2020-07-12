'''
Created on 21.06.2020

@author: thoma
'''

import pigpio
import time

INTERVAL = 200
LOOPS = 1000

def wave_test():
        pi = pigpio.pi()
        
        pi.set_mode(14, pigpio.OUTPUT)
        pi.set_mode(15, pigpio.OUTPUT)
        pi.set_mode(17, pigpio.OUTPUT)
        pi.set_mode(18, pigpio.OUTPUT)
        
        pi.wave_clear()

        next_wave_id = -1
        current_wave_id = -1
        prev_wave_id = -1
        
        # start of with a minimal delay pulse 
        pulse = pigpio.pulse(0,0,INTERVAL)
        pi.wave_add_generic([pulse])
        current_wave_id = pi.wave_create_and_pad(10)
        
        pi.wave_send_once(current_wave_id)
        

        # start of wave
        p = []
        p.append(pigpio.pulse(1<<14, 1<<18, INTERVAL))
        p.append(pigpio.pulse(1<<15, 1<<14, INTERVAL))
        p.append(pigpio.pulse(1<<17, 1<<15, INTERVAL))
        p.append(pigpio.pulse(1<<18, 1<<17, INTERVAL))
        
        delay_p = pigpio.pulse(0,0,INTERVAL)

        start = time.time_ns()


        for i in range(LOOPS):
            pi.wave_add_generic([p[i%4]])

 #           pi.wave_add_generic([p[i%4], delay_p])

            next_wave_id = pi.wave_create_and_pad(10)
            pi.wave_send_using_mode(next_wave_id, pigpio.WAVE_MODE_ONE_SHOT_SYNC)
            
#            print(f"sending p[{i%4}] [{next_wave_id}] @{time.time()}, duration {pi.wave_get_micros()}")
            
            c = 0
            while pi.wave_tx_at() == current_wave_id:
#                time.sleep(0.0001)
                c+=1
        
#            print(f"slept for {c} sleep cycles")
        
            if prev_wave_id != -1:
                pi.wave_delete(prev_wave_id)
            
            prev_wave_id = current_wave_id
            current_wave_id = next_wave_id
    
        end = time.time_ns()
        
        runtime = (end - start)/1000000
        expected = LOOPS*INTERVAL / 1000
        print(f"runtime {runtime} milliseconds. Expected runtime was {expected}")

        pi.write(14,pigpio.LOW)
        pi.write(15,pigpio.LOW)
        pi.write(17,pigpio.LOW)
        pi.write(18,pigpio.LOW)

if __name__ == '__main__':
    wave_test()