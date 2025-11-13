import random
import time
import asyncio
class HumanBehaviorSimulator:
    @staticmethod
    def random_delay(min_ms=800, max_ms=2500):
        """Random delay between actions"""
        delay = random.uniform(min_ms / 1000, max_ms / 1000)
        time.sleep(delay)
    
    @staticmethod
    async def async_random_delay(min_ms=800, max_ms=2500):
        """Async random delay between actions"""
        delay = random.uniform(min_ms / 1000, max_ms / 1000)
        await asyncio.sleep(delay)
    
    @staticmethod
    def human_typing_speed():
        """Return random typing speed in characters per minute"""
        return random.randint(180, 350)
    
    @staticmethod
    def mouse_movement_pattern(start_x, start_y, end_x, end_y):
        """Generate human-like mouse movement coordinates"""
        points = []
        num_points = random.randint(3, 8)
        
        # Control points for bezier-like curve
        control_x1 = start_x + (end_x - start_x) * random.uniform(0.2, 0.4)
        control_y1 = start_y + (end_y - start_y) * random.uniform(0.1, 0.3)
        control_x2 = start_x + (end_x - start_x) * random.uniform(0.6, 0.8)
        control_y2 = start_y + (end_y - start_y) * random.uniform(0.7, 0.9)
        
        for i in range(num_points + 1):
            t = i / num_points
            # Cubic bezier curve calculation
            x = (1-t)**3 * start_x + 3*(1-t)**2*t * control_x1 + 3*(1-t)*t**2 * control_x2 + t**3 * end_x
            y = (1-t)**3 * start_y + 3*(1-t)**2*t * control_y1 + 3*(1-t)*t**2 * control_y2 + t**3 * end_y
            
            # Add some randomness to the points
            x += random.uniform(-5, 5)
            y += random.uniform(-5, 5)
            
            points.append((x, y))
        
        return points
