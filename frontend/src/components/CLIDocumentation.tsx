import React, { useState, useEffect } from 'react';
import {
  Box,
  Heading,
  Text,
  Button,
  VStack,
  HStack,
  Code,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  List,
  ListItem,
  ListIcon,
  Divider,
  Link,
  useColorModeValue,
  Alert,
  AlertIcon,
  Spinner,
  Badge
} from '@chakra-ui/react';
import { FaDownload, FaGithub, FaTerminal, FaCheckCircle, FaBook } from 'react-icons/fa';
import { CLIInfo, getCliInfo, getCliDownloadUrl, getCliDocsUrl } from '../api/cliService';

interface CLIInfo {
  version: string;
  description: string;
  features: Record<string, string>;
  installation: Record<string, string>;
  documentation_url: string;
}

const CLIDocumentation: React.FC = () => {
  const [cliInfo, setCliInfo] = useState<CLIInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const bgColor = useColorModeValue('gray.50', 'gray.700');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  
  useEffect(() => {
    const fetchCliInfo = async () => {
      try {
        const data = await getCliInfo();
        setCliInfo(data);
        setLoading(false);
      } catch (err) {
        console.error('Failed to load CLI information:', err);
        setError('Failed to load CLI information');
        setLoading(false);
      }
    };
    
    fetchCliInfo();
  }, []);
  
  const handleDownload = () => {
    window.location.href = getCliDownloadUrl();
  };
  
  if (loading) {
    return (
      <Box textAlign="center" py={10}>
        <Spinner size="xl" />
        <Text mt={4}>Loading CLI information...</Text>
      </Box>
    );
  }
  
  if (error) {
    return (
      <Alert status="error">
        <AlertIcon />
        {error}
      </Alert>
    );
  }
  
  return (
    <Box p={8}>
      <VStack spacing={8} align="stretch">
        <Box textAlign="center">
          <Heading as="h1" size="2xl">
            Soleco CLI
          </Heading>
          <HStack justify="center" mt={2}>
            <Badge colorScheme="green" fontSize="md" py={1} px={2}>
              v{cliInfo?.version}
            </Badge>
          </HStack>
          <Text mt={4} fontSize="xl">
            {cliInfo?.description}
          </Text>
          <HStack spacing={4} justify="center" mt={6}>
            <Button 
              leftIcon={<FaDownload />} 
              colorScheme="blue" 
              size="lg"
              onClick={handleDownload}
            >
              Download CLI
            </Button>
            <Button 
              leftIcon={<FaGithub />} 
              variant="outline" 
              size="lg"
              as="a"
              href="https://github.com/yourusername/soleco"
              target="_blank"
            >
              View on GitHub
            </Button>
          </HStack>
        </Box>
        
        <Divider />
        
        <Tabs isLazy variant="enclosed">
          <TabList>
            <Tab><HStack><FaTerminal /><Text ml={2}>Features</Text></HStack></Tab>
            <Tab><HStack><FaDownload /><Text ml={2}>Installation</Text></HStack></Tab>
            <Tab><HStack><FaBook /><Text ml={2}>Usage</Text></HStack></Tab>
          </TabList>
          
          <TabPanels>
            <TabPanel>
              <Box bg={bgColor} p={6} borderRadius="md" borderWidth="1px" borderColor={borderColor}>
                <Heading as="h3" size="md" mb={4}>Key Features</Heading>
                <List spacing={3}>
                  {cliInfo && Object.entries(cliInfo.features).map(([key, value]) => (
                    <ListItem key={key}>
                      <ListIcon as={FaCheckCircle} color="green.500" />
                      <Text as="span" fontWeight="bold">{key.split('_').join(' ').replace(/\b\w/g, l => l.toUpperCase())}:</Text>{' '}
                      {value}
                    </ListItem>
                  ))}
                </List>
              </Box>
            </TabPanel>
            
            <TabPanel>
              <Box bg={bgColor} p={6} borderRadius="md" borderWidth="1px" borderColor={borderColor}>
                <Heading as="h3" size="md" mb={4}>Installation Options</Heading>
                
                <Box mb={6}>
                  <Heading as="h4" size="sm" mb={2}>Using pip</Heading>
                  <Code p={3} display="block" borderRadius="md" whiteSpace="pre">
                    {cliInfo?.installation.pip}
                  </Code>
                </Box>
                
                <Box>
                  <Heading as="h4" size="sm" mb={2}>From Source</Heading>
                  <Code p={3} display="block" borderRadius="md" whiteSpace="pre">
                    {cliInfo?.installation.source}
                  </Code>
                </Box>
              </Box>
            </TabPanel>
            
            <TabPanel>
              <Box bg={bgColor} p={6} borderRadius="md" borderWidth="1px" borderColor={borderColor}>
                <Heading as="h3" size="md" mb={4}>Basic Usage</Heading>
                
                <Box mb={6}>
                  <Heading as="h4" size="sm" mb={2}>Getting Help</Heading>
                  <Code p={3} display="block" borderRadius="md" whiteSpace="pre">
                    soleco --help
                  </Code>
                </Box>
                
                <Box mb={6}>
                  <Heading as="h4" size="sm" mb={2}>Network Status</Heading>
                  <Code p={3} display="block" borderRadius="md" whiteSpace="pre">
                    soleco network status
                  </Code>
                </Box>
                
                <Box mb={6}>
                  <Heading as="h4" size="sm" mb={2}>RPC Nodes</Heading>
                  <Code p={3} display="block" borderRadius="md" whiteSpace="pre">
                    soleco rpc list
                  </Code>
                </Box>
                
                <Box mb={6}>
                  <Heading as="h4" size="sm" mb={2}>Recent Mints</Heading>
                  <Code p={3} display="block" borderRadius="md" whiteSpace="pre">
                    soleco mint recent
                  </Code>
                </Box>
                
                <Box>
                  <Heading as="h4" size="sm" mb={2}>Interactive Shell</Heading>
                  <Code p={3} display="block" borderRadius="md" whiteSpace="pre">
                    soleco shell
                  </Code>
                </Box>
                
                <Link 
                  href={getCliDocsUrl()} 
                  color="blue.500" 
                  display="inline-block" 
                  mt={4}
                  isExternal
                >
                  View Complete Documentation →
                </Link>
              </Box>
            </TabPanel>
          </TabPanels>
        </Tabs>
      </VStack>
    </Box>
  );
};

export default CLIDocumentation;
