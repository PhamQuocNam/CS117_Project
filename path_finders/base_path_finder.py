import numpy as np
import heapq
from collections import deque
from typing import List, Tuple, Optional

class PathFinder:
    def __init__(self, config):
        """
        Initialize the PathFinder with configuration
        
        Args:
            config: Configuration object containing:
                - map_size: tuple (width, height) of the parking lot
                - initial_pos: tuple (x, y) starting position (entrance)
                - obstacles: list of (x, y) positions that are blocked
                - paths: list of (x,y) positions that not allow to park but allow vehicle to move through
        """
        self.map_size = config.map_size  # (width, height)
        self.initial_pos = config.initial_pos
        
        # Initialize 2D matrix for distances
        self.distance_matrix = [[float('inf') for _ in range(self.map_size[1])] 
                               for _ in range(self.map_size[0])]
        
        # Status matrix: 0=empty, 1=parked, 2=obstacle, 3=path_only
        self.status_matrix = [[0 for _ in range(self.map_size[1])] 
                             for _ in range(self.map_size[0])]
        
        # Lists to track positions
        self.parked_list = []  # List of parked positions
        self.blank_pos_list = []  # Min-heap of (distance, position) for empty spots
        
        # Set obstacles if provided
        if hasattr(config, 'obstacles') and config.obstacles:
            for obs_x, obs_y in config.obstacles:
                if self._is_valid_position(obs_x, obs_y):
                    self.status_matrix[obs_x][obs_y] = 2
                
        # Set path-only positions if provided
        if hasattr(config, 'paths') and config.paths:
            for x, y in config.paths:
                if self._is_valid_position(x, y):
                    self.status_matrix[x][y] = 3
        
        # Calculate distances from initial position using BFS
        self._calculate_distances()
        self._update_blank_positions()
    
    def _is_valid_position(self, x: int, y: int) -> bool:
        """Check if position is within map boundaries"""
        return 0 <= x < self.map_size[0] and 0 <= y < self.map_size[1]
    
    def _calculate_distances(self):
        """Calculate shortest distances from initial position using BFS"""
        queue = deque([(self.initial_pos[0], self.initial_pos[1], 0)])
        visited = [[False for _ in range(self.map_size[1])] 
                  for _ in range(self.map_size[0])]
        
        # 8-directional movement (including diagonals)
        directions = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1),           (0, 1),
            (1, -1),  (1, 0),  (1, 1)
        ]
        
        while queue:
            x, y, dist = queue.popleft()
            
            # Skip if already visited or invalid position
            if not self._is_valid_position(x, y) or visited[x][y]:
                continue
            
            # Skip if it's an obstacle (but allow path-only positions for movement)
            if self.status_matrix[x][y] == 2:
                continue
            
            visited[x][y] = True
            self.distance_matrix[x][y] = dist
            
            # Add neighbors to queue
            for dx, dy in directions:
                new_x, new_y = x + dx, y + dy
                if (self._is_valid_position(new_x, new_y) and 
                    not visited[new_x][new_y] and 
                    self.status_matrix[new_x][new_y] != 2):  # Allow movement through paths
                    queue.append((new_x, new_y, dist + 1))
    
    def _update_blank_positions(self):
        """Update the heap of blank positions"""
        self.blank_pos_list = []
        
        for x in range(self.map_size[0]):
            for y in range(self.map_size[1]):
                # Only include positions that are empty (0) and not path-only (3)
                if (self.status_matrix[x][y] == 0 and  # Empty and parkable
                    self.distance_matrix[x][y] != float('inf') and  # Reachable
                    (x, y) != self.initial_pos):  # Not the entrance
                    heapq.heappush(self.blank_pos_list, 
                                 (self.distance_matrix[x][y], [x, y]))
    
    def find_shortest_blank_position(self) -> Optional[Tuple[int, int]]:
        """
        Find the closest empty parking position
        
        Returns:
            tuple: (x, y) coordinates of the closest empty spot, or None if no spots available
        """
        while self.blank_pos_list:
            distance, position = heapq.heappop(self.blank_pos_list)
            x, y = position
            
            # Check if this position is still empty and parkable
            if self.status_matrix[x][y] == 0:
                return (x, y)
        
        return None  # No empty spots available
    
    def park_vehicle(self, position: Tuple[int, int]) -> bool:
        """
        Park a vehicle at the specified position
        
        Args:
            position: tuple (x, y) where to park
            
        Returns:
            bool: True if successfully parked, False otherwise
        """
        x, y = position
        
        if not self._is_valid_position(x, y):
            print(f"Invalid position: ({x}, {y})")
            return False
        
        if self.status_matrix[x][y] != 0:
            if self.status_matrix[x][y] == 3:
                print(f"Position ({x}, {y}) is a path-only area, parking not allowed")
            else:
                print(f"Position ({x}, {y}) is not empty")
            return False
        
        # Park the vehicle
        self.status_matrix[x][y] = 1
        self.parked_list.append((x, y))
        
        print(f"Vehicle parked at position ({x}, {y})")
        return True
    
    def remove_parked_position(self, position: Tuple[int, int]) -> bool:
        """
        When customers leave the parking lot, convert parked position back to blank
        
        Args:
            position: tuple (x, y) position to unpark
            
        Returns:
            bool: True if successfully unparked, False otherwise
        """
        x, y = position
        
        if not self._is_valid_position(x, y):
            print(f"Invalid position: ({x}, {y})")
            return False
        
        if self.status_matrix[x][y] != 1:
            print(f"No vehicle parked at position ({x}, {y})")
            return False
        
        # Remove the vehicle
        self.status_matrix[x][y] = 0
        if (x, y) in self.parked_list:
            self.parked_list.remove((x, y))
        
        # Add back to blank positions heap if reachable
        if self.distance_matrix[x][y] != float('inf'):
            heapq.heappush(self.blank_pos_list, 
                         (self.distance_matrix[x][y], [x, y]))
        
        print(f"Vehicle removed from position ({x}, {y})")
        return True
    
    def get_path_to_position(self, target_pos: Tuple[int, int]) -> List[Tuple[int, int]]:
        """
        Get the shortest path from initial position to target position
        
        Args:
            target_pos: tuple (x, y) destination
            
        Returns:
            list: List of (x, y) coordinates representing the path
        """
        if not self._is_valid_position(target_pos[0], target_pos[1]):
            return []
        
        # Check if target is reachable
        if self.distance_matrix[target_pos[0]][target_pos[1]] == float('inf'):
            return []
        
        path = []
        current = target_pos
        
        # Backtrack from target to initial position
        while current != self.initial_pos:
            path.append(current)
            x, y = current
            current_dist = self.distance_matrix[x][y]
            
            # Find the neighbor with the smallest distance that leads toward start
            best_neighbor = None
            min_dist = float('inf')
            
            directions = [
                (-1, -1), (-1, 0), (-1, 1),
                (0, -1),           (0, 1),
                (1, -1),  (1, 0),  (1, 1)
            ]
            
            for dx, dy in directions:
                new_x, new_y = x + dx, y + dy
                if (self._is_valid_position(new_x, new_y) and
                    self.distance_matrix[new_x][new_y] < current_dist and
                    self.distance_matrix[new_x][new_y] < min_dist):
                    min_dist = self.distance_matrix[new_x][new_y]
                    best_neighbor = (new_x, new_y)
            
            if best_neighbor is None:
                # Fallback: try to find any reachable neighbor with smaller distance
                for dx, dy in directions:
                    new_x, new_y = x + dx, y + dy
                    if (self._is_valid_position(new_x, new_y) and
                        self.distance_matrix[new_x][new_y] != float('inf') and
                        self.distance_matrix[new_x][new_y] < current_dist):
                        best_neighbor = (new_x, new_y)
                        break
                
                if best_neighbor is None:
                    return []  # No valid path found
            
            current = best_neighbor
        
        path.append(self.initial_pos)
        path.reverse()
        return path
    
    def get_parking_status(self) -> dict:
        """
        Get current parking lot status
        
        Returns:
            dict: Status information including total spots, parked, empty, etc.
        """
        total_parkable_spots = 0
        empty_spots = 0
        parked_spots = len(self.parked_list)
        obstacle_spots = 0
        path_only_spots = 0
        
        for x in range(self.map_size[0]):
            for y in range(self.map_size[1]):
                if self.distance_matrix[x][y] != float('inf'):  # Reachable positions
                    if self.status_matrix[x][y] == 0:
                        total_parkable_spots += 1
                        empty_spots += 1
                    elif self.status_matrix[x][y] == 1:
                        total_parkable_spots += 1
                    elif self.status_matrix[x][y] == 2:
                        obstacle_spots += 1
                    elif self.status_matrix[x][y] == 3:
                        path_only_spots += 1
        
        return {
            'total_parkable_spots': total_parkable_spots,
            'empty_spots': empty_spots,
            'parked_spots': parked_spots,
            'obstacle_spots': obstacle_spots,
            'path_only_spots': path_only_spots,
            'occupancy_rate': parked_spots / total_parkable_spots if total_parkable_spots > 0 else 0
        }
    
    def visualize_map(self) -> str:
        """
        Create a text visualization of the parking lot
        
        Returns:
            str: Text representation of the map
        """
        visualization = []
        
        for y in range(self.map_size[1]):
            row = []
            for x in range(self.map_size[0]):
                if (x, y) == self.initial_pos:
                    row.append('S')  # Start position
                elif self.status_matrix[x][y] == 1:
                    row.append('P')  # Parked
                elif self.status_matrix[x][y] == 2:
                    row.append('X')  # Obstacle
                elif self.status_matrix[x][y] == 3:
                    row.append('R')  # Road/Path only
                elif self.distance_matrix[x][y] == float('inf'):
                    row.append('#')  # Unreachable
                else:
                    row.append('.')  # Empty parkable spot
            visualization.append(' '.join(row))
        
        legend = "\nLegend: S=Start, P=Parked, X=Obstacle, R=Road/Path, #=Unreachable, .=Empty"
        return '\n'.join(visualization) + legend


# Configuration class for the PathFinder
class PathFinderConfig:
    def __init__(self, map_size: Tuple[int, int], initial_pos: Tuple[int, int], 
                 obstacles: List[Tuple[int, int]] = None, 
                 paths: List[Tuple[int, int]] = None):
        self.map_size = map_size
        self.initial_pos = initial_pos
        self.obstacles = obstacles or []
        self.paths = paths or []


# Example usage and testing
if __name__ == "__main__":
    # Create configuration with obstacles and paths
    config = PathFinderConfig(
        map_size=(12, 8),
        initial_pos=(0, 0),
        obstacles=[(2, 2), (2, 3), (3, 2), (3, 3), (8, 4), (9, 4)],  # Blocked areas
        paths=[(1, 0), (1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6), (1, 7),  # Vertical road
               (0, 4), (2, 4), (3, 4), (4, 4), (5, 4), (6, 4), (7, 4)]  # Horizontal road
    )
    
    # Initialize path finder
    pf = PathFinder(config)
    
    # Print initial map
    print("Initial parking lot:")
    print(pf.visualize_map())
    print()
    
    # Test parking multiple vehicles
    for i in range(5):
        closest_spot = pf.find_shortest_blank_position()
        if closest_spot:
            print(f"Vehicle {i+1} - Closest parking spot: {closest_spot}")
            success = pf.park_vehicle(closest_spot)
            
            if success:
                # Show path to the spot
                path = pf.get_path_to_position(closest_spot)
                print(f"Path to parking spot: {path}")
                print(f"Distance: {pf.distance_matrix[closest_spot[0]][closest_spot[1]]}")
        else:
            print(f"No available parking spots for vehicle {i+1}")
        print()
    
    # Show updated map
    print("After parking vehicles:")
    print(pf.visualize_map())
    print()
    
    # Show status
    status = pf.get_parking_status()
    print("Parking status:")
    for key, value in status.items():
        if key == 'occupancy_rate':
            print(f"  {key}: {value:.2%}")
        else:
            print(f"  {key}: {value}")
    
    # Test removing a parked vehicle
    if pf.parked_list:
        removed_pos = pf.parked_list[0]
        print(f"\nRemoving vehicle from {removed_pos}")
        pf.remove_parked_position(removed_pos)
        
        print("After removing vehicle:")
        print(pf.visualize_map())
        
        # Show updated status
        status = pf.get_parking_status()
        print(f"Updated occupancy rate: {status['occupancy_rate']:.2%}")