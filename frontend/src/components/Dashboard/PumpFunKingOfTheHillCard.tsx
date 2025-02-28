import {
  Box,
  Card,
  CardHeader,
  CardBody,
  Heading,
  Text,
  Image,
  Spinner,
  Flex,
  Progress,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  List,
  ListItem,
  Badge,
  useColorModeValue,
  SimpleGrid,
  Button,
  Link,
  HStack,
  Tooltip,
  Icon,
  Divider
} from '@chakra-ui/react';
import { useQuery, useQueryClient } from 'react-query';
import { pumpFunApi, KingOfTheHill } from '../../api/pumpFunService';
import { getSafeImageUrl, handleImageError } from '../../utils/imageUtils';
import { useState, useEffect } from 'react';
import { ExternalLinkIcon, LinkIcon } from '@chakra-ui/icons';
import { FaTwitter, FaTelegram } from 'react-icons/fa';

// Define interface for previous kings
interface PreviousKing {
  name: string;
  duration: number;
  mint?: string;
  symbol?: string;
}

interface PumpFunKingOfTheHillCardProps {
  includeNsfw?: boolean;
}

const PumpFunKingOfTheHillCard: React.FC<PumpFunKingOfTheHillCardProps> = ({ includeNsfw = true }) => {
  // Define color mode values at the top, before any conditional rendering
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const cardBg = useColorModeValue('gray.100', 'gray.900');
  
  const queryClient = useQueryClient();
  const { data, isLoading, error, isError, refetch } = useQuery(
    'pumpfun-king-of-the-hill',
    () => pumpFunApi.getKingOfTheHill(includeNsfw), // Use the prop value
    { 
      refetchInterval: 30000, // Refresh every 30 seconds
      retry: 2,
      retryDelay: 1000,
      onError: (err: any) => {
        console.error('Error fetching king of the hill:', err);
      }
    }
  );

  // Force refetch on component mount
  useEffect(() => {
    // Clear the cache and refetch
    queryClient.removeQueries('pumpfun-king-of-the-hill');
    refetch();
  }, []);

  const [timeRemaining, setTimeRemaining] = useState<number>(0);
  
  const handleRetry = () => {
    queryClient.invalidateQueries('pumpfun-king-of-the-hill');
  };

  // Update time remaining every second
  useEffect(() => {
    if (data) {
      // Calculate time remaining based on king_of_the_hill_timestamp
      const kingTimestamp = data.king_of_the_hill_timestamp;
      if (kingTimestamp) {
        // Convert timestamp to milliseconds if it's in seconds (Unix timestamp)
        // Timestamps in milliseconds are typically > 1,000,000,000,000
        const kingTimestampMs = kingTimestamp > 10000000000 ? kingTimestamp : kingTimestamp * 1000;
        
        // King of the hill lasts for 24 hours (86400 seconds)
        const expiryTime = kingTimestampMs + 86400000; // 24 hours in milliseconds
        const now = Date.now();
        const remainingMs = expiryTime - now;
        
        if (remainingMs > 0) {
          setTimeRemaining(Math.floor(remainingMs / 1000));
          
          const timer = setInterval(() => {
            setTimeRemaining(prev => {
              if (prev <= 0) return 0;
              return prev - 1;
            });
          }, 1000);
          
          return () => clearInterval(timer);
        } else {
          setTimeRemaining(0);
        }
      } else {
        setTimeRemaining(0);
      }
    } else {
      setTimeRemaining(0);
    }
  }, [data]);

  // Format time remaining as hh:mm:ss
  const formatTimeRemaining = (seconds: number): string => {
    if (seconds === undefined || seconds === null) return '00:00:00';
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Format timestamp to readable date
  const formatTimestamp = (timestamp: number): string => {
    if (!timestamp) return 'Unknown';
    const date = new Date(timestamp > 10000000000 ? timestamp : timestamp * 1000);
    return date.toLocaleString();
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Heading size="md">King of the Hill</Heading>
        </CardHeader>
        <CardBody>
          <Flex justify="center" align="center" h="300px">
            <Spinner size="xl" />
          </Flex>
        </CardBody>
      </Card>
    );
  }

  if (isError) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    const isRateLimitError = errorMessage.includes('429') || errorMessage.includes('rate limit');
    
    return (
      <Card>
        <CardHeader>
          <Heading size="md">King of the Hill</Heading>
        </CardHeader>
        <CardBody>
          <Box textAlign="center" py={4}>
            <Text color="red.500" mb={3}>
              {isRateLimitError 
                ? 'Pump.fun API rate limit exceeded. Please try again later.' 
                : 'Error loading King of the Hill data'}
            </Text>
            <Text fontSize="sm" color="gray.500" mb={4}>
              The Pump.fun API may be experiencing issues or rate limiting.
            </Text>
            <Button 
              colorScheme="blue" 
              size="sm"
              onClick={handleRetry}
            >
              Retry
            </Button>
          </Box>
        </CardBody>
      </Card>
    );
  }

  // Calculate progress percentage for time remaining
  const maxTime = 86400; // 24 hours in seconds
  const progressPercentage = (timeRemaining / maxTime) * 100;

  return (
    <Card>
      <CardHeader>
        <Heading size="md">Pump.fun King of the Hill</Heading>
      </CardHeader>
      <CardBody>
        <Flex direction="column" align="center" mb={6}>
          {data && data.image_uri ? (
            <Image 
              src={getSafeImageUrl(data.image_uri)}
              alt={data.name || 'King of the Hill'}
              boxSize="100px"
              borderRadius="full"
              mb={4}
              fallbackSrc="/assets/pumpfun-logo.png"
              onError={(e) => handleImageError(e)}
            />
          ) : (
            <Box 
              w="100px" 
              h="100px" 
              borderRadius="full" 
              bg="gray.200" 
              display="flex" 
              alignItems="center" 
              justifyContent="center"
              mb={4}
            >
              <Text fontSize="xl" fontWeight="bold">{data && data.symbol ? data.symbol.charAt(0) : '?'}</Text>
            </Box>
          )}
          
          <Heading size="lg" textAlign="center" mb={2}>
            {data?.name || 'Unknown Token'}
          </Heading>
          
          <Badge colorScheme="purple" mb={4}>
            {data?.symbol || 'N/A'}
          </Badge>
          
          {/* Social links */}
          <HStack spacing={4} mb={4}>
            {data?.website && (
              <Tooltip label={data.website}>
                <Link href={data.website} isExternal>
                  <Icon as={LinkIcon} boxSize={5} />
                </Link>
              </Tooltip>
            )}
            {data?.twitter && (
              <Tooltip label={data.twitter}>
                <Link href={data.twitter} isExternal>
                  <Icon as={FaTwitter} boxSize={5} color="twitter.500" />
                </Link>
              </Tooltip>
            )}
            {data?.telegram && (
              <Tooltip label={data.telegram}>
                <Link href={data.telegram} isExternal>
                  <Icon as={FaTelegram} boxSize={5} color="telegram.500" />
                </Link>
              </Tooltip>
            )}
          </HStack>
          
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4} mb={6} width="100%">
            <Stat
              p={3}
              shadow="md"
              border="1px solid"
              borderColor={borderColor}
              rounded="lg"
              bg={cardBg}
            >
              <StatLabel>Current Price</StatLabel>
              <StatNumber>
                {data?.virtual_sol_reserves && data?.virtual_token_reserves
                  ? (data.virtual_sol_reserves / (data.virtual_token_reserves / 1000000000) / 1000000000).toFixed(4)
                  : '0'} SOL
              </StatNumber>
              {data?.usd_market_cap && (
                <StatHelpText>
                  ${(data.usd_market_cap / (data.total_supply / 1000000000)).toFixed(4)} USD
                </StatHelpText>
              )}
            </Stat>
            
            <Stat
              p={3}
              shadow="md"
              border="1px solid"
              borderColor={borderColor}
              rounded="lg"
              bg={cardBg}
            >
              <StatLabel>Total Value Locked</StatLabel>
              <StatNumber>
                {data?.virtual_sol_reserves
                  ? (data.virtual_sol_reserves / 1000000000).toFixed(2)
                  : '0'} SOL
              </StatNumber>
              {data?.usd_market_cap && (
                <StatHelpText>
                  ${data.usd_market_cap.toFixed(2)} USD
                </StatHelpText>
              )}
            </Stat>
          </SimpleGrid>
          
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4} mb={6} width="100%">
            <Stat
              p={3}
              shadow="md"
              border="1px solid"
              borderColor={borderColor}
              rounded="lg"
              bg={cardBg}
            >
              <StatLabel>Created</StatLabel>
              <StatNumber fontSize="md">
                {data?.created_timestamp ? formatTimestamp(data.created_timestamp) : 'Unknown'}
              </StatNumber>
            </Stat>
            
            <Stat
              p={3}
              shadow="md"
              border="1px solid"
              borderColor={borderColor}
              rounded="lg"
              bg={cardBg}
            >
              <StatLabel>Crowned King</StatLabel>
              <StatNumber fontSize="md">
                {data?.king_of_the_hill_timestamp ? formatTimestamp(data.king_of_the_hill_timestamp) : 'Unknown'}
              </StatNumber>
            </Stat>
          </SimpleGrid>
          
          <Box w="100%" mb={4}>
            <Flex justify="space-between" mb={1}>
              <Text fontWeight="bold">Time Remaining</Text>
              <Text>{formatTimeRemaining(timeRemaining)}</Text>
            </Flex>
            <Progress 
              value={progressPercentage} 
              colorScheme="purple" 
              size="sm" 
              borderRadius="md"
            />
          </Box>
          
          {data?.description && (
            <Box w="100%" mb={4}>
              <Divider my={4} />
              <Text fontWeight="bold" mb={2}>Description</Text>
              <Text fontSize="sm">{data.description}</Text>
            </Box>
          )}
        </Flex>
        
        {data?.previous_kings && data.previous_kings.length > 0 && (
          <Box>
            <Heading size="sm" mb={3}>Previous Kings</Heading>
            <List spacing={2}>
              {data.previous_kings.slice(0, 5).map((king: PreviousKing, index: number) => (
                <ListItem key={index}>
                  <Flex justify="space-between">
                    <Text fontWeight={index === 0 ? "bold" : "normal"}>
                      {king.name}
                    </Text>
                    <Text>
                      {Math.floor(king.duration / 60)} min {king.duration % 60} sec
                    </Text>
                  </Flex>
                </ListItem>
              ))}
            </List>
          </Box>
        )}
        <Button 
          colorScheme="blue" 
          size="sm"
          onClick={() => {
            queryClient.removeQueries('pumpfun-king-of-the-hill');
            refetch();
          }}
        >
          Refetch
        </Button>
      </CardBody>
    </Card>
  );
};

export default PumpFunKingOfTheHillCard;
