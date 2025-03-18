import React from 'react';
import { IconButton, Tooltip, useColorModeValue } from '@chakra-ui/react';
import { RepeatIcon } from '@chakra-ui/icons';

interface RefreshButtonProps {
  onClick: () => void;
  isLoading?: boolean;
  tooltipLabel?: string;
  size?: string;
  'aria-label'?: string;
}

/**
 * A reusable refresh button component with loading state
 */
const RefreshButton: React.FC<RefreshButtonProps> = ({
  onClick,
  isLoading = false,
  tooltipLabel = 'Refresh data',
  size = 'sm',
  'aria-label': ariaLabel = 'Refresh data',
}) => {
  const iconColor = useColorModeValue('blue.500', 'blue.300');

  return (
    <Tooltip label={tooltipLabel} hasArrow placement="top">
      <IconButton
        icon={<RepeatIcon />}
        onClick={onClick}
        isLoading={isLoading}
        size={size}
        aria-label={ariaLabel}
        variant="ghost"
        color={iconColor}
        _hover={{ bg: useColorModeValue('blue.50', 'blue.900') }}
        isRound
      />
    </Tooltip>
  );
};

export default RefreshButton;
