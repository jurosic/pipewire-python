from subprocess import call as subprocess_call
from subprocess import check_output as subprocess_check_output
import json

"""
    If connectNodes gets fed a discionary thats longer than one node, call an error
"""

class Linker:
    _cls_instance = None
    
    def __new__(self, *args):
        if not self._cls_instance:
            self._cls_instance = super().__new__(self)
        return self._cls_instance
    
    def __init__(self):
        """Initializes the PipeWireLinker class."""
        self._links = {}
        self._nodes = {}
        self._update()
        
    def connectNodes(self, node0:dict, node1:dict):
        out = {}
        for port in node0['output']:
            out[port] = self.connect(node0['output'][port], node1["input"][port])
        return out
    
    def connect(self, port0:int, port1:int):
        """
        Connects two ports together with a link.
            Has no effect if the ports are already connected.
            If the ports arent connected, it calls self.__pwlinkConnect.
        
            Args:
                port0 (int): The first (output) port to connect.
                port1 (int): The second (input) port to connect.
            
            Returns:
                (list): [(bool) success, (str) return message]
        """
        
        self._update()
        
        if port1 in self._links:
            if port0 in self._links[port1]:
                return [True, "already connected"]
            
            else:
                self.__pwlinkConnect(port0, port1)
                return [True, "connected"]
            
        else:
            self.__pwlinkConnect(port0, port1)
            return [True, f"connected, created new entry."]
        
    def __pwlinkConnect(self, port0:int, port1:int):
        """Connects two ports using pw-link."""
        subprocess_call(["pw-link", str(port0), str(port1)])
    
    def disconnectNodes(self, node0:dict, node1:dict):
        out = {}
        for port in node0['output']:
            out[port] = self.disconnect(node0['output'][port], node1["input"][port])
        return out
    
    def disconnect(self, port0:int, port1:int):
        """
        Disconnects two ports and terminates link.
            Has no effect if the ports are already disconnected.
            If the ports arent disconnected, it calls self.__pwlinkDisconnect.
        
            Args:
                port0 (int): The first (output) port to disconnect.
                port1 (int): The second (input) port to disconnect.
            
            Returns:
                (list): [(bool) success, (str) return message]
        """

        self._update()
        
        if port1 in self._links:
            if port0 in self._links[port1]:
                self.__pwlinkDisconnect(port0, port1)
                return [True, "disconnected"]
            
            else:
                return [True, "already disconnected"]
            
        else:
            return [True, f"already disconnected, no entry."]
        
    def __pwlinkDisconnect(self, port0:int, port1:int):
        "Disconnects two ports using pw-link."
        subprocess_call(["pw-link", "-d", str(port0), str(port1)])
        
    def getNodesByName(self, name:str):
        self._update()
        out = {}
        for node in self._nodes:
            if name in node:
                out[node] = self._nodes[node]
                
        return out
    
    def findNewNodes(self):
        """
        Finds new nodes that have been added since the last update.
        Returns only their names, not their ports.
        """
        old_nodes = self._nodes.copy()
        self._update()
        return list(set(self._nodes) - set(old_nodes))

    def _update(self):
        """
        Updates the PipeWireLinker class.
            Goes through the process of getting every port
            or link and updating the internal variables.    

            Args:
                None
            Returns:
                True/False based on success
        """
        
        self._links = {}
        self._nodes = {}
        
        output_ports = subprocess_check_output(["pw-link", "-Io"]).decode("utf-8").split("\n")
        input_ports = subprocess_check_output(["pw-link", "-Ii"]).decode("utf-8").split("\n")
        links = subprocess_check_output(["pw-link", "-Il"]).decode("utf-8").split("\n")
        
        """Get rid of empty lines and strip whitespace"""
        input_ports = [x.strip(" ") for x in input_ports if x != ""]
        output_ports = [x.strip(" ") for x in output_ports if x != ""]
        links = [x.strip(" ") for x in links if x != ""]
        
        """INPUT PORT PARSING"""
        """Explanation to this bullshittery is below in Output Port Parsing"""
        pos = {}
        for port in input_ports:
            split_port = port.split(" ")
            node = "".join(split_port[1:]).split(":")
            node_name = node[0]
            
            pos[node_name] = 0
        
        for port in input_ports:
            split_port = port.split(" ")
            port_int = int(split_port[0])
            
            """Get the whole node name, since it was split at spaces. Node name ends with a colon."""
            node = "".join(split_port[1:]).split(":")
            node_name = node[0] + "_" + str(pos[node[0]])
            node_properties = node[1]
            node_channel = "".join(node_properties[-2:])
            
            """If the node is not a valid audio node, skip it. Exp. Midi-Bridge"""
            if node_channel != "FL" and node_channel != "FR": #This limits everything to stereo
                continue
            
            """If the node is not in the dictionary, add it"""
            if node_name not in self._nodes:
                self._nodes[node_name] = {}
            if "input" not in self._nodes[node_name]:
                self._nodes[node_name]["input"] = {}
            if node_channel not in self._nodes[node_name]["input"]:
                self._nodes[node_name]["input"][node_channel] = port_int
            else:                              
                """
                A bit more complex. If there is an existing node in the dicrionary, but there is another
                node that exists, we need to make a different named entry in the dictionary. So we take the position
                of the node, and add 1 to it. This is a bit of a hack, but it works.
                """
                pos[node[0]] += 1
                
                pos_node_name = node[0] + "_" + str(int(pos[node[0]]))
                if pos_node_name not in self._nodes:
                    self._nodes[pos_node_name] = {}
                if "input" not in self._nodes[pos_node_name]:
                    self._nodes[pos_node_name]["input"] = {}
                if node_channel not in self._nodes[pos_node_name]["input"]:
                    self._nodes[pos_node_name]["input"][node_channel] = port_int
                
        """OUTPUT PORT PARSING"""
        """
        Declaring the variable 'pos', what this does is it declares the starting position of the node_name.
        In the beginnig this is always zero, 1 gets added to the node, every time it is already found to be in the dictionary.
        Why is 'pos' a dictionary? If it wasn't it wouldnt work. Imagine this is the output:
            Firefox
            Firefox
            Node
            Firefox
            
        the positions would look like this:
            0
            1
            0
            0
            
        which means the previous dictionary entry would be overwritten.
        my head hurts..
        """
        pos = {}
        for port in output_ports:
            split_port = port.split(" ")
            node = "".join(split_port[1:]).split(":")
            node_name = node[0]
            
            pos[node_name] = 0
        
        for port in output_ports:
            split_port = port.split(" ")
            port_int = int(split_port[0])
            
            """Get the whole node name, since it was split at spaces. Node name ends with a colon."""
            node = "".join(split_port[1:]).split(":")
            """Here we add _0 to the node name to 'kickstart' the node positions"""
            node_name = node[0] + "_" + str(pos[node[0]])
            node_properties = node[1]
            node_channel = "".join(node_properties[-2:])
            
            """If the node is not a valid audio node, skip it. Exp. Midi-Bridge"""
            if node_channel != "FL" and node_channel != "FR": #This limits everythign to stereo
                continue
            
            """If the node is not in the dictionary, add it"""
            if node_name not in self._nodes:
                self._nodes[node_name] = {}
            if 'output' not in self._nodes[node_name]:
                self._nodes[node_name]['output'] = {}
            if node_channel not in self._nodes[node_name]['output']:
                self._nodes[node_name]['output'][node_channel] = port_int
            else:                                
                """
                A bit more complex. If there is an existing node in the dicrionary, but there is another
                node that exists, we need to make a different named entry in the dictionary. So we take the position
                of the node, and add 1 to it. This is a bit of a hack, but it works.
                """
                pos[node[0]] += 1
                
                pos_node_name = node[0] + "_" + str(int(pos[node[0]]))
                if pos_node_name not in self._nodes:
                    self._nodes[pos_node_name] = {}
                if 'output' not in self._nodes[pos_node_name]:
                    self._nodes[pos_node_name]['output'] = {}
                if node_channel not in self._nodes[pos_node_name]['output']:
                    self._nodes[pos_node_name]['output'][node_channel] = port_int
            
        """LINK PARSING"""
        """
        This is a bit more complicated, first we declare node_port_int outside of the loop
        so that it can be used in the next loop. 
        We check with |<- if the link is an input link, and if it is, we add it to the dictionary.
        if not, we redefine node_port_int to be the output port of the next link.
        In the end we clean up the dictionary by removing the keys that have empty lists in them.
        This is because the loop also gets the output ports, which we don't need.
        
        Example:
        113 (input port id) alsa_output.pci-0000_00_1f.3.analog-stereo:playback_FL
        87 (link id)  |<-  127 (output port id) Firefox:output_FL
        63 (link id)  |<-  259 (output port id) Firefox:output_FL
        
        That was the example of a good link, we can use it.
        The loop also thinks that the link ids are node input ports, so we need to remove them.
        Removing them is easy, since their key in the dictionary will be an empty list.
        
        The keys in the self._links dictionary are the node input ports.
        
        Dict structure is as follows:
        {
            node_input_port: [list of output ports]
        }
        """
        
        node_port_int = None
        for line in links:
            split_line = line.split(" ")
            
            if "|<-" not in line:
                node_port_int = int(split_line[0])
                if node_port_int not in self._links:
                    self._links[node_port_int] = []
            else:
                cnter = 0
                while True:
                    if split_line[split_line.index("|<-")+1+cnter] == "":
                        cnter += 1
                    else:
                        self._links[node_port_int].append(int(split_line[split_line.index("|<-")+1+cnter]))
                        break
                    
        """Remove the keys that have link ids in them. We use list() to avoid a RuntimeError"""
        for link in list(self._links.keys()):
            if self._links[link] == []:
                del self._links[link]
                
    def __json__(self):
        """Returns a json string of the class vars."""
        return json.dumps(self.__dict__, indent=4)
    
if __name__ == "__main__":
    pwl = Linker()
    a = pwl.getNodeByName("Firefox")
    b = pwl.getNodeByName("alsa_output")
    print(json.dumps(a, indent=4))
    print(json.dumps(b, indent=4))
    pwl.disconnectNodes(a[list(a)[0]], b[list(b)[0]])
    
    print(pwl.__json__())